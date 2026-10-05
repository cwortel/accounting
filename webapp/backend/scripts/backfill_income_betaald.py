"""One-off backfill: sync Income.betaald with whether a bank transaction is linked.

Before the link endpoints started auto-syncing betaald, income rows that were
already linked to a bank transaction kept showing "Open" on the Inkomsten page.

Usage (run from webapp/backend/):
    python -m scripts.backfill_income_betaald
"""

from sqlalchemy import select

from app.database import SessionLocal
from app.models import BankTransaction, Income


def main() -> None:
    with SessionLocal() as db:
        linked_ids = set(
            db.execute(select(BankTransaction.income_id).where(BankTransaction.income_id.is_not(None))).scalars()
        )
        updated = 0
        for income in db.execute(select(Income)).scalars():
            should_be_paid = income.id in linked_ids
            if income.betaald != should_be_paid:
                income.betaald = should_be_paid
                updated += 1
        db.commit()
        print(f"Updated {updated} income rows")


if __name__ == "__main__":
    main()
