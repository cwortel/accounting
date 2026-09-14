"""Monthly cash-flow aggregates powering the Prognose forecast page."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import schemas


def get_monthly_cashflow(db: Session) -> list[schemas.MonthlyCashflow]:
    inc_rows = db.execute(text(
        "SELECT strftime('%Y-%m', datum) as maand, SUM(total) as omzet "
        "FROM income WHERE datum IS NOT NULL AND datum!='' AND total>0 "
        "GROUP BY maand"
    )).all()
    exp_rows = db.execute(text(
        "SELECT strftime('%Y-%m', datum) as maand, SUM(total) as kosten "
        "FROM expenses WHERE datum IS NOT NULL AND datum!='' AND total>0 AND categorie!='Taxes' "
        "GROUP BY maand"
    )).all()
    prive_rows = db.execute(text(
        "SELECT strftime('%Y-%m', datum) as maand, SUM(ABS(bedrag)) as prive_out "
        "FROM bank_transactions WHERE prive=1 AND bedrag<0 "
        "AND rekening IN (SELECT iban FROM rekeningen WHERE type='zakelijk' AND categorie='betaalrekening') "
        "GROUP BY maand"
    )).all()
    btw_rows = db.execute(text(
        "SELECT strftime('%Y-%m', datum) as maand, SUM(ABS(bedrag)) as btw_paid "
        "FROM bank_transactions WHERE btw_betaling=1 "
        "GROUP BY maand"
    )).all()
    rec_rows = db.execute(text(
        "SELECT strftime('%Y-%m', datum) as maand, SUM(ABS(bedrag)) as totaal "
        "FROM bank_transactions WHERE is_recurring=1 AND bedrag<0 "
        "AND rekening IN (SELECT iban FROM rekeningen WHERE type='prive') "
        "GROUP BY maand"
    )).all()
    spend_rows = db.execute(text(
        "SELECT strftime('%Y-%m', datum) as maand, SUM(ABS(bedrag)) as totaal "
        "FROM bank_transactions WHERE bedrag<0 "
        "AND rekening IN (SELECT iban FROM rekeningen WHERE type='prive') "
        "GROUP BY maand"
    )).all()

    def to_map(rows, col):
        return {r.maand: float(getattr(r, col) or 0) for r in rows if r.maand}

    omzet_map = to_map(inc_rows, "omzet")
    kosten_map = to_map(exp_rows, "kosten")
    prive_map = to_map(prive_rows, "prive_out")
    btw_map = to_map(btw_rows, "btw_paid")
    rec_map = to_map(rec_rows, "totaal")
    spend_map = to_map(spend_rows, "totaal")

    all_months = sorted(
        set(omzet_map) | set(kosten_map) | set(prive_map) | set(btw_map) | set(rec_map) | set(spend_map)
    )
    return [
        schemas.MonthlyCashflow(
            maand=m,
            omzet=omzet_map.get(m, 0),
            kosten=kosten_map.get(m, 0),
            prive_out=prive_map.get(m, 0),
            btw_paid=btw_map.get(m, 0),
            recurring_prive=rec_map.get(m, 0),
            totaal_prive_uitgaven=spend_map.get(m, 0),
        )
        for m in all_months
    ]
