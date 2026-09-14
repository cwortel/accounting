from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_api_key

router = APIRouter(prefix="/accounts", tags=["accounts"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[schemas.Rekening])
def list_accounts(db: Session = Depends(get_db)):
    stmt = select(models.Rekening).order_by(models.Rekening.type, models.Rekening.categorie, models.Rekening.naam)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=schemas.Rekening)
def create_account(payload: schemas.RekeningCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(models.Rekening).where(models.Rekening.iban == payload.iban.upper())
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Account with this IBAN already exists")
    account = models.Rekening(
        **payload.model_dump(exclude={"iban", "laatste_update"}),
        iban=payload.iban.upper(),
        laatste_update=payload.laatste_update.isoformat() if payload.laatste_update else "",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=schemas.Rekening)
def update_account(account_id: int, payload: schemas.RekeningCreate, db: Session = Depends(get_db)):
    account = db.get(models.Rekening, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in payload.model_dump(exclude={"iban", "laatste_update"}).items():
        setattr(account, field, value)
    account.iban = payload.iban.upper()
    account.laatste_update = payload.laatste_update.isoformat() if payload.laatste_update else ""
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(models.Rekening, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()
