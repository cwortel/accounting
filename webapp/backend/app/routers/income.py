from datetime import date as _date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_api_key
from ..services import matching

router = APIRouter(prefix="/income", tags=["income"], dependencies=[Depends(require_api_key)])


def _compute_btw(total: float, btw_pct: int) -> tuple[float, float]:
    ex_btw = round(total / (1 + btw_pct / 100), 2) if btw_pct > 0 else round(total, 2)
    btw = round(total - ex_btw, 2)
    return ex_btw, btw


@router.get("", response_model=list[schemas.Income])
def list_income(jaar: int, kwartaal: int | None = None, db: Session = Depends(get_db)):
    stmt = select(models.Income).where(models.Income.jaar == jaar)
    if kwartaal:
        stmt = stmt.where(models.Income.kwartaal == kwartaal)
    stmt = stmt.order_by(models.Income.datum, models.Income.factuur)
    income_rows = db.execute(stmt).scalars().all()

    tx_by_income = {
        tx.income_id: tx
        for tx in db.execute(
            select(models.BankTransaction).where(
                models.BankTransaction.income_id.in_([i.id for i in income_rows])
            )
        ).scalars()
    }
    for income in income_rows:
        tx = tx_by_income.get(income.id)
        income.linked_transaction = schemas.BankTxSummary.model_validate(tx) if tx else None
    return income_rows


@router.get("/{income_id}/bank-match-candidates", response_model=list[schemas.BankTxMatchCandidate])
def income_bank_match_candidates(income_id: int, db: Session = Depends(get_db)):
    income = db.get(models.Income, income_id)
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")

    candidates = db.execute(
        select(models.BankTransaction).where(
            models.BankTransaction.jaar == income.jaar,
            models.BankTransaction.bedrag > 0,
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
        score = matching.score_income(income, abs(float(tx.bedrag)), tx_date, tx.naam, tx.referentie)
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


@router.post("", response_model=schemas.Income)
def create_income(payload: schemas.IncomeCreate, db: Session = Depends(get_db)):
    ex_btw, btw = _compute_btw(payload.total, payload.btw_pct)
    income = models.Income(
        **payload.model_dump(exclude={"datum"}),
        datum=payload.datum.isoformat() if payload.datum else "",
        ex_btw=ex_btw,
        btw=btw,
    )
    db.add(income)
    db.commit()
    db.refresh(income)
    return income


@router.put("/{income_id}", response_model=schemas.Income)
def update_income(income_id: int, payload: schemas.IncomeUpdate, db: Session = Depends(get_db)):
    income = db.get(models.Income, income_id)
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    ex_btw, btw = _compute_btw(payload.total, payload.btw_pct)
    for field, value in payload.model_dump(exclude={"datum"}).items():
        setattr(income, field, value)
    income.datum = payload.datum.isoformat() if payload.datum else ""
    income.ex_btw = ex_btw
    income.btw = btw
    db.commit()
    db.refresh(income)
    return income


@router.delete("/{income_id}", status_code=204)
def delete_income(income_id: int, db: Session = Depends(get_db)):
    income = db.get(models.Income, income_id)
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    for tx in db.execute(
        select(models.BankTransaction).where(models.BankTransaction.income_id == income_id)
    ).scalars():
        tx.income_id = None
        tx.fooi = 0
    db.delete(income)
    db.commit()
