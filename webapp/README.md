# Webapp rebuild (FastAPI + Next.js)

New version of the accounting app, coexisting with the legacy Streamlit app
at the repo root (`../Dashboard.py`). Nothing here touches the old app or its
database until you explicitly run the migration script.

## Run locally

```bash
./start.sh
```

Sets up the backend venv and frontend `node_modules` on first run (and copies
the `.env` files from their examples if missing), then starts both servers.
Press Ctrl+C to stop both. Open http://localhost:3000.

Note: the auto-created `.env` files use a placeholder API token — fine for
local dev since both sides get the same placeholder, but replace it with a
real random value in `backend/.env` (and match it in `frontend/.env.local`)
before this app leaves your machine.

<details>
<summary>Run manually instead</summary>

Terminal 1 — backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set ACCOUNTING_API_TOKEN
uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend
npm install
cp .env.local.example .env.local   # BACKEND_API_KEY must match ACCOUNTING_API_TOKEN above
npm run dev
```

</details>

## What's here

- `backend/` — FastAPI + SQLAlchemy API, schema mirrors the legacy SQLite
  database so migration (`backend/scripts/migrate_from_old_db.py`) is a
  straight copy. See [backend/README.md](backend/README.md).
- `frontend/` — Next.js (App Router) + Tailwind + shadcn/ui. Server Components
  fetch data straight from the API; mutations go through Server Actions in
  `frontend/src/app/actions.ts`. The backend API key is never sent to the
  browser (`frontend/src/lib/api.ts` is `server-only`).

## Current feature coverage

- Dashboard: KPI cards, per-kwartaal chart, BTW aangifte detail, kosten per categorie.
- Uitgaven / Inkomsten: list + create/edit dialog + delete + filters (naam,
  categorie, afgerekend-status, kwartaal) + totals row.
- Transacties: **scoped to zakelijk accounts only** (fixed a critical bug where
  the original build showed private transactions mixed in), filters
  (kwartaal, alleen ongekoppeld, naam, categorie), metrics bar, betaal/spaar
  split, match dialog with 5 types (Uitgave/Inkomst/Privé/Intern/BTW betaling)
  + create-expense-from-transaction.
- Rekeningen: full CRUD, zakelijk/privé saldo summary cards, per-account
  transaction stats, bank file import (manual upload or scan the shared
  `data/BankTransactions/` folder).
- Prognose: full cash-flow forecast — buffer targets, run-rate projection,
  BTW payment schedule, debt obligations, saldo projection chart. Beginsaldo
  persists via the backend `app_settings` table.
- Privé: KPI cards (incl. vaste lasten, gem. p/m, schuld restant/termijnen
  p/m), category breakdown (Vaste lasten / Leningen / Overig), filters
  (maand, rekening, naam, categorie, ongecategoriseerd, alleen vast), inline
  category/recurring editing (applies to all transactions with the same naam,
  matching legacy behavior). No pagination — not needed at current data volume.
- Schulden: list + create/edit/delete.

Note: `vaste_lasten` and `prive_inkomsten` are confirmed-removed legacy
concepts (not just unused — intentionally dropped) and have been deleted
from the new backend entirely (models, schemas, migration script).

Not yet ported: receipt attachments.

## Data migration

Real data has been migrated from the legacy app into
`webapp/backend/data/accounting.db` via `backend/scripts/migrate_from_old_db.py`.
Re-run it any time to refresh from the legacy database (it replaces rows in the
new DB, so it's safe to re-run, but any edits made only in the new app since the
last migration would be overwritten).
