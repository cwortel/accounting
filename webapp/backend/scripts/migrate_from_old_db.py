"""One-off migration: copy all rows from the legacy Streamlit SQLite DB
(data/boekhouding.db) into the new backend's database (webapp/backend/data/accounting.db).

The table/column layout is intentionally identical between the two apps, so this
is a straight table-by-table copy rather than a data transformation.

Usage (run from webapp/backend/):
    python -m scripts.migrate_from_old_db [--old-db /path/to/boekhouding.db]
"""

import argparse
import sqlite3
from pathlib import Path

from app.database import DB_PATH

OLD_DB_DEFAULT = Path(__file__).resolve().parents[3] / "data" / "boekhouding.db"

TABLES = [
    "categories",
    "expenses",
    "income",
    "bank_transactions",
    "rekeningen",
    "schulden",
]


def migrate(old_db_path: Path, new_db_path: Path) -> None:
    if not old_db_path.exists():
        raise SystemExit(f"Old database not found: {old_db_path}")
    if not new_db_path.exists():
        raise SystemExit(
            f"New database not found at {new_db_path}. "
            "Start the backend once (it creates the schema on boot) before migrating."
        )

    old_conn = sqlite3.connect(old_db_path)
    old_conn.row_factory = sqlite3.Row
    new_conn = sqlite3.connect(new_db_path)

    for table in TABLES:
        try:
            rows = old_conn.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            print(f"skip {table}: not present in old database")
            continue
        if not rows:
            print(f"{table}: nothing to migrate")
            continue

        columns = rows[0].keys()
        new_cols = {r[1] for r in new_conn.execute(f"PRAGMA table_info({table})").fetchall()}
        common_columns = [c for c in columns if c in new_cols]
        placeholders = ",".join("?" for _ in common_columns)
        col_list = ",".join(common_columns)

        new_conn.execute(f"DELETE FROM {table}")
        new_conn.executemany(
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
            [[row[c] for c in common_columns] for row in rows],
        )
        new_conn.commit()
        print(f"{table}: migrated {len(rows)} rows")

    old_conn.close()
    new_conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-db", type=Path, default=OLD_DB_DEFAULT)
    args = parser.parse_args()
    migrate(args.old_db, DB_PATH)
