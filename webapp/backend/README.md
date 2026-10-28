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

Receipt OCR also needs the Tesseract binary + Dutch language pack installed
system-wide (used via `pytesseract`; `pymupdf`/Pillow are pure Python and
already covered by `pip install`):

```bash
brew install tesseract tesseract-lang   # macOS
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

## Receipt OCR

Scanned/photographed receipts (PDF or image) placed in `data/Receipts/`
(repo root, configurable via `Settings.receipts_dir`), organized in quarter
subfolders like `2026-Q1/`, are picked up by `POST /receipts/scan`: it walks
the folder recursively, OCRs any new file (by content hash — re-running is
always safe), and stores a pending `Receipt` row with best-effort extracted
fields (naam, datum, totaal, BTW%). Files are never moved or modified.

Review/approve each pending receipt via `GET /receipts?status=pending`,
`POST /receipts/{id}/approve` (creates the linked `Expense`) or
`POST /receipts/{id}/reject`. The frontend exposes this as the "Bonnetjes
controleren" tab on the Uitgaven page.
