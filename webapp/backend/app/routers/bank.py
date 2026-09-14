import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import get_settings
from ..database import get_db
from ..deps import require_api_key
from ..services import bank_import, matching

router = APIRouter(prefix="/bank-transactions", tags=["bank"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[schemas.BankTransaction])
def list_bank_transactions(
    jaar: int,
    kwartaal: int | None = None,
    only_unmatched: bool = False,
    rekening: str | None = None,
    rekening_type: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(models.BankTransaction).where(models.BankTransaction.jaar == jaar)
    if kwartaal:
        stmt = stmt.where(models.BankTransaction.kwartaal == kwartaal)
    if only_unmatched:
        stmt = stmt.where(
            models.BankTransaction.expense_id.is_(None),
            models.BankTransaction.income_id.is_(None),
            models.BankTransaction.prive.is_(False),
            models.BankTransaction.intern.is_(False),
            models.BankTransaction.btw_betaling.is_(False),
        )
    if rekening:
        stmt = stmt.where(models.BankTransaction.rekening == rekening)
    if rekening_type:
        zakelijk_ibans = select(models.Rekening.iban).where(models.Rekening.type == rekening_type)
        stmt = stmt.where(models.BankTransaction.rekening.in_(zakelijk_ibans))
    stmt = stmt.order_by(models.BankTransaction.datum, models.BankTransaction.id)
    return db.execute(stmt).scalars().all()


@router.post("/import/camt", response_model=schemas.ImportResult)
async def import_camt(file: UploadFile, db: Session = Depends(get_db)):
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename or "camt.xml").suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        # Preserve the original filename for dedup bookkeeping.
        renamed = Path(tmp_path).with_name(file.filename or Path(tmp_path).name)
        Path(tmp_path).rename(renamed)
        count = bank_import.import_camt(db, str(renamed))
    finally:
        Path(renamed).unlink(missing_ok=True)
    return schemas.ImportResult(bestand=file.filename or "", aantal_toegevoegd=count)


@router.post("/import/rabobank-csv", response_model=schemas.ImportResult)
async def import_rabobank_csv(file: UploadFile, db: Session = Depends(get_db)):
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename or "export.csv").suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        renamed = Path(tmp_path).with_name(file.filename or Path(tmp_path).name)
        Path(tmp_path).rename(renamed)
        count = bank_import.import_rabobank_csv(db, str(renamed))
    finally:
        Path(renamed).unlink(missing_ok=True)
    return schemas.ImportResult(bestand=file.filename or "", aantal_toegevoegd=count)


@router.post("/import/scan-folder", response_model=list[schemas.ImportResult])
def import_scan_folder(db: Session = Depends(get_db)):
    """Import every CAMT.053 XML / Rabobank CSV file from the shared BankTransactions folder."""
    folder = get_settings().bank_transactions_dir
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder}")

    results = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() == ".xml":
            count = bank_import.import_camt(db, str(path))
        elif path.suffix.lower() == ".csv":
            count = bank_import.import_rabobank_csv(db, str(path))
        else:
            continue
        results.append(schemas.ImportResult(bestand=path.name, aantal_toegevoegd=count))
    return results


def _get_tx(db: Session, tx_id: int) -> models.BankTransaction:
    tx = db.get(models.BankTransaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Bank transaction not found")
    return tx


@router.post("/{tx_id}/link", response_model=schemas.BankTransaction)
def link_bank_transaction(tx_id: int, payload: schemas.LinkBankTransaction, db: Session = Depends(get_db)):
    tx = _get_tx(db, tx_id)
    tx.expense_id = payload.expense_id
    tx.income_id = payload.income_id
    tx.fooi = round(payload.fooi, 2)
    tx.prive = False
    tx.prive_omschrijving = ""
    if payload.expense_id:
        expense = db.get(models.Expense, payload.expense_id)
        if expense:
            expense.afgerekend = True
            expense.betaal_bron = "Bank zakelijk"
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/{tx_id}/unlink", response_model=schemas.BankTransaction)
def unlink_bank_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = _get_tx(db, tx_id)
    tx.expense_id = None
    tx.income_id = None
    tx.fooi = 0
    tx.prive = False
    tx.prive_omschrijving = ""
    tx.intern = False
    tx.intern_omschrijving = ""
    tx.btw_betaling = False
    tx.btw_betaling_jaar = None
    tx.btw_betaling_kwartaal = None
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/{tx_id}/mark-prive", response_model=schemas.BankTransaction)
def mark_prive(tx_id: int, payload: schemas.MarkPrive, db: Session = Depends(get_db)):
    tx = _get_tx(db, tx_id)
    tx.prive = True
    tx.prive_omschrijving = payload.omschrijving.strip()
    tx.expense_id = None
    tx.income_id = None
    tx.fooi = 0
    tx.intern = False
    tx.intern_omschrijving = ""
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/{tx_id}/mark-intern", response_model=schemas.BankTransaction)
def mark_intern(tx_id: int, payload: schemas.MarkIntern, db: Session = Depends(get_db)):
    tx = _get_tx(db, tx_id)
    tx.intern = True
    tx.intern_omschrijving = payload.omschrijving.strip()
    tx.expense_id = None
    tx.income_id = None
    tx.fooi = 0
    tx.prive = False
    tx.prive_omschrijving = ""
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/{tx_id}/mark-btw-betaling", response_model=schemas.BankTransaction)
def mark_btw_betaling(tx_id: int, payload: schemas.MarkBtwBetaling, db: Session = Depends(get_db)):
    tx = _get_tx(db, tx_id)
    tx.btw_betaling = True
    tx.btw_betaling_jaar = payload.jaar
    tx.btw_betaling_kwartaal = payload.kwartaal
    tx.expense_id = None
    tx.income_id = None
    tx.fooi = 0
    tx.prive = False
    tx.prive_omschrijving = ""
    tx.intern = False
    tx.intern_omschrijving = ""
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/{tx_id}/match-candidates", response_model=list[schemas.MatchCandidate])
def match_candidates(tx_id: int, db: Session = Depends(get_db)):
    tx = _get_tx(db, tx_id)
    amt = abs(float(tx.bedrag))
    tx_datum = tx.datum if isinstance(tx.datum, str) else str(tx.datum)
    from datetime import date as _date

    tx_date = _date.fromisoformat(tx_datum[:10])

    candidates = db.execute(
        select(models.Expense).where(
            models.Expense.jaar == tx.jaar,
            models.Expense.afgerekend.is_(False),
        )
    ).scalars()

    scored = []
    for expense in candidates:
        score = matching.score_expense(expense, amt, tx_date, tx.naam, tx.referentie)
        if score < 0:
            continue
        fooi = round(amt - float(expense.total or 0), 2)
        scored.append(
            schemas.MatchCandidate(
                expense_id=expense.id,
                naam=expense.naam,
                datum=_date.fromisoformat(str(expense.datum)[:10]) if expense.datum else None,
                total=expense.total,
                score=score,
                fooi=max(fooi, 0),
            )
        )
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:8]


@router.get("/{tx_id}/income-match-candidates", response_model=list[schemas.IncomeMatchCandidate])
def income_match_candidates(tx_id: int, db: Session = Depends(get_db)):
    tx = _get_tx(db, tx_id)
    amt = abs(float(tx.bedrag))
    tx_datum = tx.datum if isinstance(tx.datum, str) else str(tx.datum)
    from datetime import date as _date

    tx_date = _date.fromisoformat(tx_datum[:10])

    candidates = db.execute(
        select(models.Income).where(
            models.Income.jaar == tx.jaar,
            models.Income.betaald.is_(False),
        )
    ).scalars()

    scored = []
    for income in candidates:
        score = matching.score_income(income, amt, tx_date, tx.naam, tx.referentie)
        if score < 0:
            continue
        scored.append(
            schemas.IncomeMatchCandidate(
                income_id=income.id,
                naam=income.naam,
                datum=_date.fromisoformat(str(income.datum)[:10]) if income.datum else None,
                total=income.total,
                score=score,
            )
        )
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:8]


@router.post("/{tx_id}/create-expense", response_model=schemas.Expense)
def create_expense_from_transaction(tx_id: int, payload: schemas.CreateExpenseFromBank, db: Session = Depends(get_db)):
    tx = _get_tx(db, tx_id)
    if float(tx.bedrag or 0) >= 0:
        raise HTTPException(status_code=400, detail="Alleen afschrijvingen kunnen als uitgave worden aangemaakt.")
    if tx.expense_id is not None or tx.income_id is not None or tx.prive or tx.intern:
        raise HTTPException(status_code=400, detail="Deze transactie is al verwerkt. Ontkoppel eerst indien nodig.")

    total = round(abs(float(tx.bedrag or 0)), 2)
    pct = int(payload.btw_pct or 0)
    ex_btw = round(total / (1 + pct / 100), 2) if pct > 0 else total
    btw = round(total - ex_btw, 2)

    expense = models.Expense(
        factuur=payload.factuur.strip(),
        naam=(payload.naam or tx.naam or "Bankuitgave").strip(),
        datum=tx.datum,
        categorie=(payload.categorie or "Taxes").strip(),
        btw_pct=pct,
        btw=btw,
        ex_btw=ex_btw,
        total=total,
        afgerekend=True,
        betaal_bron="Bank zakelijk",
        jaar=tx.jaar,
        kwartaal=tx.kwartaal,
    )
    db.add(expense)
    db.flush()

    tx.expense_id = expense.id
    tx.income_id = None
    tx.fooi = 0
    tx.prive = False
    tx.prive_omschrijving = ""
    tx.intern = False
    tx.intern_omschrijving = ""

    db.commit()
    db.refresh(expense)
    return expense
