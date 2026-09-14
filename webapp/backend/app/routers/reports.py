from fastapi import APIRouter, Depends

from .. import schemas
from ..database import get_db
from ..deps import require_api_key
from ..services import btw as btw_service
from ..services import cashflow as cashflow_service
from sqlalchemy.orm import Session

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_api_key)])


@router.get("/yearly-summary", response_model=list[schemas.YearlyQuarterSummary])
def yearly_summary(jaar: int, db: Session = Depends(get_db)):
    return btw_service.yearly_summary(db, jaar)


@router.get("/expense-by-category", response_model=list[schemas.CategoryQuarterBreakdown])
def expense_by_category(jaar: int, db: Session = Depends(get_db)):
    return btw_service.expense_by_category_quarter(db, jaar)


@router.get("/btw-betalingen")
def btw_betalingen(jaar: int, db: Session = Depends(get_db)):
    return btw_service.btw_betalingen(db, jaar)


@router.get("/btw-aangifte")
def btw_aangifte(jaar: int, db: Session = Depends(get_db)):
    """Per-quarter 1a/5b aangifte breakdown, matching the legacy Dashboard detail view."""
    income_rows, expense_rows = btw_service.btw_by_quarter(db, jaar)
    aftrek_by_q = {kw: float(btw or 0) for kw, btw in expense_rows}

    per_kwartaal: dict[int, dict] = {
        q: {"kwartaal": q, "grondslag_21": 0.0, "btw_21": 0.0, "grondslag_9": 0.0, "btw_9": 0.0}
        for q in (1, 2, 3, 4)
    }
    for kwartaal, btw_pct, grondslag, btw in income_rows:
        bucket = per_kwartaal[kwartaal]
        if btw_pct == 21:
            bucket["grondslag_21"] += float(grondslag or 0)
            bucket["btw_21"] += float(btw or 0)
        elif btw_pct == 9:
            bucket["grondslag_9"] += float(grondslag or 0)
            bucket["btw_9"] += float(btw or 0)

    result = []
    for q, bucket in per_kwartaal.items():
        aftrek = aftrek_by_q.get(q, 0.0)
        saldo = bucket["btw_21"] + bucket["btw_9"] - aftrek
        result.append({**bucket, "aftrekbare_btw": aftrek, "saldo": saldo})
    return result


@router.get("/monthly-cashflow", response_model=list[schemas.MonthlyCashflow])
def monthly_cashflow(db: Session = Depends(get_db)):
    """All-time monthly aggregates used for the Prognose cash-flow forecast."""
    return cashflow_service.get_monthly_cashflow(db)
