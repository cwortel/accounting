from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_api_key

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
    return db.execute(stmt).scalars().all()


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
