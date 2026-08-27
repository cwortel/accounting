# Green Light Boekhouding

Streamlit-based accounting app for a Dutch sole trader (eenmanszaak / ZZP).  
Run with: `streamlit run Dashboard.py`

Data is stored in `data/boekhouding.db` (SQLite).  
Bank export files (CAMT.053 XML and Rabobank CSV) go in `data/BankTransactions/`.

---

## Pages

### 💚 Dashboard (`Dashboard.py`)
Year-level overview.

- **Top metrics** — omzet, kosten, winst, BTW saldo (all ex BTW).
- **Per kwartaal table** — omzet, kosten, winst, BTW breakdown per quarter.
- **Aangifte detail** — expandable per-quarter BTW declaration summary (1a/5b), shows whether the quarterly BTW has been paid (✅) or not (⚠️).
- **Kosten per categorie** — horizontal bar chart + pivot table of expenses by category across quarters. "Taxes" category is excluded from all totals here.
- Sidebar: year selector.

---

### 📊 Zakelijk Overzicht (`pages/1_Zakelijk_Overzicht.py`)
Edit income and expenses per quarter.

- **Inkomsten table** — editable grid: naam, datum, project, BTW%, totaal. Ex BTW and BTW are calculated automatically. "Betaald" is checked automatically when a bank transaction is linked.
- **Uitgaven table** — editable grid: naam, datum, categorie, BTW%, totaal. Same auto-calculation. Shows payment source when matched to a bank transaction.
- Both tables have a **totals row** at the bottom.
- Save buttons persist changes to the database.
- Sidebar: year + quarter selector.

---

### 🏦 Zakelijke Transacties (`pages/2_Zakelijke_Transacties.py`)
Match bank transactions to invoices.

- **Filters (sidebar)** — year, quarter, "alleen ongekoppeld", naam search, category dropdown (Alle / Uitgave / Inkomst / Interne overboeking / Privé onttrekking / BTW betaling / Ongekoppeld).
- **Metrics bar** — totals for gekoppeld, privé, intern, BTW betaling, betaal/spaar split.
- **Import** — expandable panel to import CAMT.053 and Rabobank CSV files.
- **Each transaction row expands** to show:
  - Left: naam, van/naar IBAN, referentie, bedrag.
  - Right (action panel), depending on status:
    - 🟢 **Gekoppeld** — shows linked invoice (naam · datum · factuurnummer · bedrag); unlink button.
    - 🔄 **Interne overboeking** — label + unlink.
    - 🟡 **Privé onttrekking** — label + unlink.
    - 📘 **BTW betaling** — quarter/year + unlink.
    - 🔴/🔵 **Ongekoppeld** — match form: choose type (Uitgave / Inkomst / Privé onttrekking / Interne overboeking / BTW betaling), then pick/create the matching record.
- **Spaarrekening** shown in a collapsed expander at the bottom.

**Linking an expense** — the app scores candidates by amount, date proximity and name match, shows the top 8. If the bank amount is higher than the invoice a tip/fooi field appears.  
**Creating a new expense from a transaction** — available at the bottom of the Uitgave match form when no existing expense fits.  
**BTW betaling** — marks the transaction as payment of a quarterly VAT obligation; appears as ✅ Betaald in the Dashboard aangifte detail.

---

### 🏦 Rekeningen & Saldo (`pages/3_Rekeningen.py`)
Account overview and import.

- **Saldo overview** — current balance per account (updated from the latest imported bank statement).
- **Import** — button to import all CAMT/CSV files from `data/BankTransactions/`.
- **Rekeningen table** — editable list of known accounts (naam, IBAN, type, categorie, saldo).

---

### 🏠 Privé Dashboard (`pages/4_Prive_Dashboard.py`)
Personal spending overview (separate from the business P&L).

- **Top metrics** — inkomsten, uitgaven, netto, vaste lasten, gemiddelde vaste lasten p/m, schuld restant, schuld termijnen p/m.
- **Kosten per categorie chart** — horizontal bar chart of private spending by category (with recurring costs highlighted).
- **Uitgaven table** — filterable by naam, categorie, recurring flag. Inline category and recurring assignment; changes auto-apply to all transactions with the same naam.
- **Inkomsten table** — filterable incoming transactions.
- **Schulden** — editable table tracking loans/debts: termijnen, restant, verwacht klaar.
- Sidebar: year, month, rekening selector, toggle for paid-off debts.

---

## Data flow

```
Bank export files (XML / CSV)
        │
        ▼
  Rekeningen page — import
        │
        ▼
  bank_transactions table
        │
   ┌────┴────┐
   │         │
expenses   income     ← entered / edited in Zakelijk Overzicht
   │         │
   └────┬────┘
        │
  Dashboard + BTW aangifte
```

## Categories (zakelijk)
`Administration` · `Car Expenses` · `Office` · `Representation` · `Travel`

BTW payments are tracked as **BTW betaling** bank transactions — not as expenses.
