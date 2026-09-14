from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_api_key

router = APIRouter(prefix="/categories", tags=["categories"], dependencies=[Depends(require_api_key)])

DEFAULT_CATEGORIES = ["Administration", "Car Expenses", "Office", "Representation", "Travel"]


@router.get("", response_model=list[str])
def list_categories(db: Session = Depends(get_db)):
    managed = {row[0] for row in db.execute(select(models.Category.naam)).all()}
    used = {
        row[0]
        for row in db.execute(
            select(models.Expense.categorie).where(
                models.Expense.categorie != "", models.Expense.categorie != "Taxes"
            )
        ).all()
    }
    return sorted(managed | used)


@router.post("", response_model=schemas.Category)
def create_category(naam: str, db: Session = Depends(get_db)):
    existing = db.execute(select(models.Category).where(models.Category.naam == naam)).scalar_one_or_none()
    if existing:
        return existing
    category = models.Category(naam=naam)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
