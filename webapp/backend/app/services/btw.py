from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas


def yearly_summary(db: Session, jaar: int) -> list[schemas.YearlyQuarterSummary]:
    income_rows = dict(
        db.execute(
            select(models.Income.kwartaal, func.sum(models.Income.ex_btw))
            .where(models.Income.jaar == jaar)
            .group_by(models.Income.kwartaal)
        ).all()
    )
    income_btw_rows = dict(
        db.execute(
            select(models.Income.kwartaal, func.sum(models.Income.btw))
            .where(models.Income.jaar == jaar)
            .group_by(models.Income.kwartaal)
        ).all()
    )
    expense_rows = dict(
        db.execute(
            select(models.Expense.kwartaal, func.sum(models.Expense.ex_btw))
            .where(models.Expense.jaar == jaar, models.Expense.categorie != "Taxes")
            .group_by(models.Expense.kwartaal)
        ).all()
    )
    expense_btw_rows = dict(
        db.execute(
            select(models.Expense.kwartaal, func.sum(models.Expense.btw))
            .where(models.Expense.jaar == jaar, models.Expense.categorie != "Taxes")
            .group_by(models.Expense.kwartaal)
        ).all()
    )

    result = []
    for q in (1, 2, 3, 4):
        omzet = float(income_rows.get(q) or 0)
        kosten = float(expense_rows.get(q) or 0)
        btw_in = float(income_btw_rows.get(q) or 0)
        btw_uit = float(expense_btw_rows.get(q) or 0)
        result.append(
            schemas.YearlyQuarterSummary(
                kwartaal=q,
                omzet=omzet,
                kosten=kosten,
                winst=omzet - kosten,
                btw_in=btw_in,
                btw_uit=btw_uit,
                btw_saldo=btw_in - btw_uit,
            )
        )
    return result


def btw_by_quarter(db: Session, jaar: int):
    """Return (income_rows, expense_rows) grouped like the legacy 1a/5b aangifte detail."""
    income_rows = db.execute(
        select(
            models.Income.kwartaal,
            models.Income.btw_pct,
            func.sum(models.Income.ex_btw).label("grondslag"),
            func.sum(models.Income.btw).label("btw"),
        )
        .where(models.Income.jaar == jaar)
        .group_by(models.Income.kwartaal, models.Income.btw_pct)
    ).all()
    expense_rows = db.execute(
        select(models.Expense.kwartaal, func.sum(models.Expense.btw).label("aftrekbare_btw"))
        .where(models.Expense.jaar == jaar, models.Expense.categorie != "Taxes")
        .group_by(models.Expense.kwartaal)
    ).all()
    return income_rows, expense_rows


def expense_by_category_quarter(db: Session, jaar: int) -> list[schemas.CategoryQuarterBreakdown]:
    rows = db.execute(
        select(
            models.Expense.categorie,
            models.Expense.kwartaal,
            func.sum(models.Expense.ex_btw).label("totaal"),
        )
        .where(models.Expense.jaar == jaar, models.Expense.categorie != "Taxes")
        .group_by(models.Expense.categorie, models.Expense.kwartaal)
    ).all()

    by_categorie: dict[str, dict[int, float]] = {}
    for categorie, kwartaal, totaal in rows:
        by_categorie.setdefault(categorie, {})[kwartaal] = float(totaal or 0)

    result = []
    for categorie, per_kwartaal in by_categorie.items():
        q1, q2, q3, q4 = (per_kwartaal.get(q, 0.0) for q in (1, 2, 3, 4))
        result.append(
            schemas.CategoryQuarterBreakdown(
                categorie=categorie, q1=q1, q2=q2, q3=q3, q4=q4, totaal=q1 + q2 + q3 + q4
            )
        )
    result.sort(key=lambda r: r.totaal, reverse=True)
    return result


def btw_betalingen(db: Session, jaar: int) -> dict[int, dict]:
    rows = db.execute(
        select(models.BankTransaction).where(
            models.BankTransaction.btw_betaling.is_(True),
            models.BankTransaction.btw_betaling_jaar == jaar,
        )
    ).scalars()
    result: dict[int, dict] = {}
    for tx in rows:
        if tx.btw_betaling_kwartaal:
            result[tx.btw_betaling_kwartaal] = {
                "tx_id": tx.id,
                "datum": tx.datum,
                "bedrag": tx.bedrag,
            }
    return result
