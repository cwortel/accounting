import hashlib
import re
from datetime import date as _date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import get_settings
from ..database import get_db
from ..deps import require_api_key
from ..services import expense_rules, matching, receipt_ocr, ubl_invoice

router = APIRouter(prefix="/receipts", tags=["receipts"], dependencies=[Depends(require_api_key)])

RECEIPT_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png"}
_FOLDER_QUARTER_RE = re.compile(r"(\d{4})[-_ ]?Q(\d)", re.IGNORECASE)


def _derive_jaar_kwartaal_from_path(relative_dirs: tuple[str, ...]) -> tuple[int, int] | None:
    for part in relative_dirs:
        m = _FOLDER_QUARTER_RE.search(part)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def _compute_btw(total: float, btw_pct: int) -> tuple[float, float]:
    ex_btw = round(total / (1 + btw_pct / 100), 2) if btw_pct > 0 else round(total, 2)
    btw = round(total - ex_btw, 2)
    return ex_btw, btw


def _get_receipt(db: Session, receipt_id: int) -> models.Receipt:
    receipt = db.get(models.Receipt, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


def _extract_fields(primary: Path, suffix: str) -> tuple[dict, str, str]:
    """Returns (fields, raw_text, mime_type) — UBL XML sidecar data when present, else OCR."""
    xml_path = primary if suffix == ".xml" else primary.with_suffix(".xml")
    ubl_fields = ubl_invoice.parse_ubl_invoice(xml_path) if xml_path.exists() else None
    if ubl_fields is not None:
        text = xml_path.read_text(encoding="utf-8", errors="replace")
        mime_type = "application/xml" if suffix == ".xml" else receipt_ocr.MIME_TYPES.get(suffix, "application/octet-stream")
        return ubl_fields, text, mime_type
    text, mime_type = receipt_ocr.extract_text(primary)
    return receipt_ocr.parse_fields(text), text, mime_type


@router.post("/scan", response_model=schemas.ReceiptScanResult)
def scan_receipts(db: Session = Depends(get_db)):
    """Walk Settings.receipts_dir recursively and store any new file as a pending Receipt.

    If a file has a same-named .xml sidecar (a UBL e-invoice, as produced by some
    receipt-scanning apps), its exact structured data is used instead of OCR. Files
    are never moved or modified — dedup is by content hash, so re-running this after
    dropping a new file into a quarter folder is always safe.
    """
    folder = get_settings().receipts_dir
    folder.mkdir(parents=True, exist_ok=True)

    existing_hashes = set(db.execute(select(models.Receipt.file_hash)).scalars())

    today = _date.today()
    gevonden = 0
    nieuw = 0
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in RECEIPT_SUFFIXES:
            primary = path
        elif suffix == ".xml" and not any(path.with_suffix(ext).exists() for ext in RECEIPT_SUFFIXES):
            # An XML sidecar with no matching PDF/image is itself the only source we have.
            primary = path
        else:
            continue

        gevonden += 1
        file_hash = hashlib.sha256(primary.read_bytes()).hexdigest()
        if file_hash in existing_hashes:
            continue

        relative = primary.relative_to(folder)
        fields, text, mime_type = _extract_fields(primary, suffix)

        datum = fields.get("datum")
        jaar_kwartaal = _derive_jaar_kwartaal_from_path(relative.parts[:-1])
        if jaar_kwartaal:
            jaar, kwartaal = jaar_kwartaal
        elif datum:
            jaar, kwartaal = datum.year, (datum.month - 1) // 3 + 1
        else:
            jaar, kwartaal = today.year, (today.month - 1) // 3 + 1

        db.add(
            models.Receipt(
                file_path=str(relative),
                file_hash=file_hash,
                original_filename=primary.name,
                mime_type=mime_type,
                jaar=jaar,
                kwartaal=kwartaal,
                status="pending",
                extracted_naam=fields.get("naam") or "",
                extracted_datum=datum.isoformat() if datum else "",
                extracted_total=fields.get("total"),
                extracted_btw_pct=fields.get("btw_pct"),
                ocr_text=text,
                created_at=today.isoformat(),
            )
        )
        existing_hashes.add(file_hash)
        nieuw += 1

    db.commit()
    return schemas.ReceiptScanResult(gevonden=gevonden, nieuw=nieuw)


@router.get("", response_model=list[schemas.Receipt])
def list_receipts(status: str = "pending", db: Session = Depends(get_db)):
    stmt = select(models.Receipt)
    if status != "alle":
        stmt = stmt.where(models.Receipt.status == status)
    stmt = stmt.order_by(models.Receipt.created_at, models.Receipt.id)
    return db.execute(stmt).scalars().all()


@router.post("/{receipt_id}/reprocess", response_model=schemas.Receipt)
def reprocess_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """Resets a rejected receipt back to pending and re-runs extraction with the
    current logic (e.g. after a receipt was rejected by mistake, or to pick up
    extraction fixes made since it was first scanned).

    Refused for already-approved receipts: those are already linked to a real
    Expense, and resetting them to pending risks the user approving a duplicate.
    """
    receipt = _get_receipt(db, receipt_id)
    if receipt.status == "approved":
        raise HTTPException(status_code=400, detail="Deze bon is al goedgekeurd en gekoppeld aan een uitgave.")

    path = get_settings().receipts_dir / receipt.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Receipt file missing on disk")

    fields, text, _mime = _extract_fields(path, path.suffix.lower())
    datum = fields.get("datum")
    receipt.status = "pending"
    receipt.processed_at = None
    receipt.extracted_naam = fields.get("naam") or ""
    receipt.extracted_datum = datum.isoformat() if datum else ""
    receipt.extracted_total = fields.get("total")
    receipt.extracted_btw_pct = fields.get("btw_pct")
    receipt.ocr_text = text
    db.commit()
    db.refresh(receipt)
    return receipt


@router.get("/{receipt_id}/file")
def get_receipt_file(receipt_id: int, db: Session = Depends(get_db)):
    receipt = _get_receipt(db, receipt_id)
    path = get_settings().receipts_dir / receipt.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Receipt file missing on disk")
    return FileResponse(
        path,
        media_type=receipt.mime_type or None,
        filename=receipt.original_filename,
        content_disposition_type="inline",
    )


@router.get("/{receipt_id}/bank-match-candidates", response_model=list[schemas.BankTxMatchCandidate])
def receipt_bank_match_candidates(
    receipt_id: int,
    naam: str | None = None,
    total: float | None = None,
    datum: _date | None = None,
    db: Session = Depends(get_db),
):
    """Same scoring as expenses, but against the receipt's (or currently edited) fields.

    No Expense exists yet at this point in the review flow, so a transient,
    never-persisted Expense is built just to reuse matching.score_expense as-is.
    """
    receipt = _get_receipt(db, receipt_id)
    probe = models.Expense(
        naam=naam if naam is not None else receipt.extracted_naam,
        total=total if total is not None else (receipt.extracted_total or 0),
        datum=datum.isoformat() if datum else receipt.extracted_datum,
    )

    candidates = db.execute(
        select(models.BankTransaction).where(
            models.BankTransaction.jaar == receipt.jaar,
            models.BankTransaction.bedrag < 0,
            models.BankTransaction.expense_id.is_(None),
            models.BankTransaction.income_id.is_(None),
            models.BankTransaction.prive.is_(False),
            models.BankTransaction.intern.is_(False),
            models.BankTransaction.btw_betaling.is_(False),
        )
    ).scalars()

    scored = []
    for tx in candidates:
        tx_datum = tx.datum if isinstance(tx.datum, str) else str(tx.datum)
        tx_date = _date.fromisoformat(tx_datum[:10])
        score = matching.score_expense(probe, abs(float(tx.bedrag)), tx_date, tx.naam, tx.referentie)
        if score < 0:
            continue
        scored.append(
            schemas.BankTxMatchCandidate(
                tx_id=tx.id,
                naam=tx.naam,
                datum=tx_date,
                bedrag=tx.bedrag,
                referentie=tx.referentie,
                score=score,
            )
        )
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:8]


@router.post("/{receipt_id}/approve", response_model=schemas.Expense)
def approve_receipt(receipt_id: int, payload: schemas.ReceiptApprove, db: Session = Depends(get_db)):
    receipt = _get_receipt(db, receipt_id)
    if receipt.status == "approved":
        raise HTTPException(status_code=400, detail="Receipt already approved")

    datum = payload.datum or _date.today()
    ex_btw, btw = _compute_btw(payload.total, payload.btw_pct)
    expense = models.Expense(
        factuur=payload.factuur,
        naam=payload.naam,
        datum=datum.isoformat(),
        categorie=payload.categorie,
        btw_pct=payload.btw_pct,
        total=round(payload.total, 2),
        ex_btw=ex_btw,
        btw=btw,
        afgerekend=expense_rules.auto_voldaan(payload.betaal_bron),
        betaal_bron=payload.betaal_bron,
        jaar=datum.year,
        kwartaal=(datum.month - 1) // 3 + 1,
    )
    db.add(expense)
    db.flush()

    receipt.status = "approved"
    receipt.expense_id = expense.id
    receipt.processed_at = _date.today().isoformat()

    db.commit()
    db.refresh(expense)
    return expense


@router.post("/{receipt_id}/reject", response_model=schemas.Receipt)
def reject_receipt(receipt_id: int, db: Session = Depends(get_db)):
    receipt = _get_receipt(db, receipt_id)
    receipt.status = "rejected"
    receipt.processed_at = _date.today().isoformat()
    db.commit()
    db.refresh(receipt)
    return receipt
