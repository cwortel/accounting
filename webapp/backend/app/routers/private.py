from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_api_key

router = APIRouter(prefix="/private", tags=["private"], dependencies=[Depends(require_api_key)])


@router.get("/transactions", response_model=list[schemas.BankTransaction])
def private_spending(
    jaar: int,
    maand: int | None = None,
    rekening: str | None = None,
    only_costs: bool = False,
    db: Session = Depends(get_db),
):
    stmt = select(models.BankTransaction).where(models.BankTransaction.jaar == jaar)
    if only_costs:
        stmt = stmt.where(models.BankTransaction.bedrag < 0)
    if rekening:
        stmt = stmt.where(models.BankTransaction.rekening == rekening)
    else:
        prive_ibans = select(models.Rekening.iban).where(models.Rekening.type == "prive")
        stmt = stmt.where(models.BankTransaction.rekening.in_(prive_ibans))
    stmt = stmt.order_by(models.BankTransaction.datum.desc(), models.BankTransaction.id.desc())
    rows = db.execute(stmt).scalars().all()
    if maand:
        rows = [r for r in rows if str(r.datum)[5:7] == f"{maand:02d}"]
    return rows


@router.post("/transactions/{tx_id}/categorie")
def set_categorie(tx_id: int, categorie: str, apply_to_naam: bool = False, db: Session = Depends(get_db)):
    tx = db.get(models.BankTransaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Bank transaction not found")
    if apply_to_naam:
        rows = db.execute(select(models.BankTransaction).where(models.BankTransaction.naam == tx.naam)).scalars()
        count = 0
        for row in rows:
            row.prive_categorie = categorie.strip()
            count += 1
        db.commit()
        return {"updated": count}
    tx.prive_categorie = categorie.strip()
    db.commit()
    return {"updated": 1}


@router.post("/transactions/{tx_id}/recurring")
def set_recurring(tx_id: int, is_recurring: bool, apply_to_naam: bool = False, db: Session = Depends(get_db)):
    tx = db.get(models.BankTransaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Bank transaction not found")
    if apply_to_naam:
        rows = db.execute(select(models.BankTransaction).where(models.BankTransaction.naam == tx.naam)).scalars()
        count = 0
        for row in rows:
            row.is_recurring = is_recurring
            count += 1
        db.commit()
        return {"updated": count}
    tx.is_recurring = is_recurring
    db.commit()
    return {"updated": 1}


def _huidig_restant(payload: schemas.SchuldCreate) -> float:
    return max(
        0.0,
        round(payload.origineel_bedrag - payload.termijn_bedrag * payload.betaald_termijnen - payload.extra_betaald, 2),
    )


@router.get("/debts", response_model=list[schemas.Schuld])
def list_debts(only_actief: bool = False, db: Session = Depends(get_db)):
    stmt = select(models.Schuld)
    if only_actief:
        stmt = stmt.where(models.Schuld.actief.is_(True))
    stmt = stmt.order_by(models.Schuld.actief.desc(), models.Schuld.naam)
    return db.execute(stmt).scalars().all()


@router.post("/debts", response_model=schemas.Schuld)
def create_debt(payload: schemas.SchuldCreate, db: Session = Depends(get_db)):
    debt = models.Schuld(
        **payload.model_dump(exclude={"start_datum", "betaaldatum"}),
        start_datum=payload.start_datum.isoformat() if payload.start_datum else "",
        betaaldatum=payload.betaaldatum.isoformat() if payload.betaaldatum else "",
        huidig_restant=_huidig_restant(payload),
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt


@router.put("/debts/{debt_id}", response_model=schemas.Schuld)
def update_debt(debt_id: int, payload: schemas.SchuldCreate, db: Session = Depends(get_db)):
    debt = db.get(models.Schuld, debt_id)
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    for field, value in payload.model_dump(exclude={"start_datum", "betaaldatum"}).items():
        setattr(debt, field, value)
    debt.start_datum = payload.start_datum.isoformat() if payload.start_datum else ""
    debt.betaaldatum = payload.betaaldatum.isoformat() if payload.betaaldatum else ""
    debt.huidig_restant = _huidig_restant(payload)
    db.commit()
    db.refresh(debt)
    return debt


@router.delete("/debts/{debt_id}", status_code=204)
def delete_debt(debt_id: int, db: Session = Depends(get_db)):
    debt = db.get(models.Schuld, debt_id)
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    db.delete(debt)
    db.commit()
