from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_api_key

router = APIRouter(prefix="/expenses", tags=["expenses"], dependencies=[Depends(require_api_key)])


def _compute_btw(total: float, btw_pct: int) -> tuple[float, float]:
    ex_btw = round(total / (1 + btw_pct / 100), 2) if btw_pct > 0 else round(total, 2)
    btw = round(total - ex_btw, 2)
    return ex_btw, btw


def _derive_kwartaal(datum: date | None, fallback: int) -> int:
    if datum is None:
        return fallback
    return (datum.month - 1) // 3 + 1


@router.get("", response_model=list[schemas.Expense])
def list_expenses(jaar: int, kwartaal: int | None = None, db: Session = Depends(get_db)):
    stmt = select(models.Expense).where(models.Expense.jaar == jaar)
    if kwartaal:
        stmt = stmt.where(models.Expense.kwartaal == kwartaal)
    stmt = stmt.order_by(models.Expense.datum, models.Expense.factuur)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=schemas.Expense)
def create_expense(payload: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    ex_btw, btw = _compute_btw(payload.total, payload.btw_pct)
    expense = models.Expense(
        **payload.model_dump(exclude={"datum"}),
        datum=payload.datum.isoformat() if payload.datum else "",
        ex_btw=ex_btw,
        btw=btw,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.post("/quick-capture", response_model=schemas.Expense)
def quick_capture_expense(payload: schemas.ExpenseQuickCapture, db: Session = Depends(get_db)):
    """Fast-path expense creation, e.g. from a mobile OCR capture app."""
    datum = payload.datum or date.today()
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
        afgerekend=False,
        betaal_bron=payload.betaal_bron,
        jaar=datum.year,
        kwartaal=_derive_kwartaal(datum, 1),
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.put("/{expense_id}", response_model=schemas.Expense)
def update_expense(expense_id: int, payload: schemas.ExpenseUpdate, db: Session = Depends(get_db)):
    expense = db.get(models.Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    ex_btw, btw = _compute_btw(payload.total, payload.btw_pct)
    for field, value in payload.model_dump(exclude={"datum"}).items():
        setattr(expense, field, value)
    expense.datum = payload.datum.isoformat() if payload.datum else ""
    expense.ex_btw = ex_btw
    expense.btw = btw
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.get(models.Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.execute(
        select(models.BankTransaction).where(models.BankTransaction.expense_id == expense_id)
    )
    for tx in db.execute(
        select(models.BankTransaction).where(models.BankTransaction.expense_id == expense_id)
    ).scalars():
        tx.expense_id = None
        tx.fooi = 0
    db.delete(expense)
    db.commit()
