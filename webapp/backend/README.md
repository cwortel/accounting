# Backend (FastAPI)

New API-first backend for the accounting rebuild. Runs alongside the existing
Streamlit app (`../../Dashboard.py`) — nothing here touches the old app or its
database (`data/boekhouding.db`) until you explicitly run the migration script.

## Setup

```bash
cd webapp/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set ACCOUNTING_API_TOKEN to a real random value
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Docs at http://localhost:8000/docs. All routes (except `/health`) require an
`X-API-Key` header matching `ACCOUNTING_API_TOKEN`.

The new database lives at `webapp/backend/data/accounting.db` and is created
automatically on first run — it is separate from the old app's database.

## Migrate data from the old app

Once you're ready to bring your real data over:

```bash
# with the backend already run at least once (so the new schema exists)
python -m scripts.migrate_from_old_db
```

This copies every row from `data/boekhouding.db` into the new database,
table by table. Safe to re-run — it replaces existing rows in the new DB
each time.
