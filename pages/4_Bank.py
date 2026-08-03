import streamlit as st
import pandas as pd
from pathlib import Path
from db import (
    init_db, import_camt, import_rabobank_csv, get_bank_transactions,
    get_expenses, get_income, link_bank_transaction, unlink_bank_transaction,
    mark_bank_as_prive,
)

st.set_page_config(page_title="Bank", page_icon="🏦", layout="wide")
init_db()


def _score_expense(exp_row, amt: float, tx_datum, tx_naam: str, tx_ref: str) -> int:
    """Score an expense as a match candidate. Returns -1 if disqualified."""
    exp_total = float(exp_row.get("total") or 0)
    if exp_total <= 0:
        return -1
    ratio = amt / exp_total
    # Disqualify: bank paid less than 95% or tip would exceed 25%
    if ratio < 0.95 or ratio > 1.25:
        return -1

    score = 0

    # Amount: near-exact match scores highest; large tip scores low
    if ratio <= 1.005:
        score += 10
    elif ratio <= 1.10:
        score += 6
    elif ratio <= 1.20:
        score += 2
    else:
        score += 0  # 20-25% tip: allowed but unlikely

    # Date proximity: receipts are typically paid same day or within a week
    try:
        exp_date = pd.to_datetime(str(exp_row["datum"])).date()
        days = abs((tx_datum - exp_date).days)
        if days == 0:
            score += 10
        elif days <= 2:
            score += 7
        elif days <= 7:
            score += 3
        elif days <= 14:
            score += 1
        else:
            return -1  # dates too far apart
    except Exception:
        pass

    # Name: supplier name in bank naam or referentie (case-insensitive)
    hay = (str(tx_naam) + " " + str(tx_ref)).lower()
    exp_naam = str(exp_row.get("naam") or "").lower().strip()
    if exp_naam and exp_naam in hay:
        score += 10
    else:
        # Try longest word ≥4 chars from expense name
        words = sorted([w for w in exp_naam.split() if len(w) >= 4], key=len, reverse=True)
        if words and words[0] in hay:
            score += 5

    return score


def _score_income(inc_row, amt: float, tx_datum, tx_naam: str, tx_ref: str) -> int:
    """Score an income entry as a match for a credit transaction."""
    inc_total = float(inc_row.get("total") or 0)
    if inc_total <= 0:
        return -1
    ratio = amt / inc_total
    # Credits should be close to invoice total (no tips on income)
    if ratio < 0.95 or ratio > 1.05:
        return -1

    score = 0
    if ratio <= 1.005:
        score += 10
    else:
        score += 4

    try:
        inc_date = pd.to_datetime(str(inc_row["datum"])).date()
        days = abs((tx_datum - inc_date).days)
        if days <= 7:
            score += 10
        elif days <= 30:
            score += 5
        elif days <= 60:
            score += 1
        else:
            return -1
    except Exception:
        pass

    hay = (str(tx_naam) + " " + str(tx_ref)).lower()
    inc_naam = str(inc_row.get("naam") or "").lower().strip()
    if inc_naam and inc_naam in hay:
        score += 10
    else:
        words = sorted([w for w in inc_naam.split() if len(w) >= 4], key=len, reverse=True)
        if words and words[0] in hay:
            score += 5

    return score

BANK_DIR = Path(__file__).parent.parent / "data" / "BankTransactions"

st.title("🏦 Banktransacties")

if "jaar" not in st.session_state:
    st.session_state["jaar"] = 2026

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024], key="jaar")
kw_label = st.sidebar.selectbox("Kwartaal", ["Alle", "Q1", "Q2", "Q3", "Q4"])
kw_num = None if kw_label == "Alle" else int(kw_label[1])
only_unmatched = st.sidebar.checkbox("Alleen ongekoppeld", value=False)

# Always filter to business accounts only
ZAKELIJK_IBANS = ["NL84RABO0188971130", "NL49RABO3161681290"]

# ── Import ─────────────────────────────────────────────────────────────────────
with st.expander("📂 Importeer bestanden", expanded=False):
    xml_files = sorted(BANK_DIR.glob("*.xml")) if BANK_DIR.exists() else []
    csv_files = sorted(BANK_DIR.glob("*.csv")) if BANK_DIR.exists() else []
    files = xml_files + csv_files
    if files:
        st.write(f"Gevonden in `{BANK_DIR}`:")
        for f in files:
            st.code(f"{f.name} ({'CAMT' if f.suffix == '.xml' else 'CSV'})")
        if st.button("⬆️ Importeer alle bestanden", type="primary"):
            total = 0
            for f in xml_files:
                n = import_camt(str(f))
                total += n
                st.write(f"  `{f.name}` → {n} nieuwe transacties")
            for f in csv_files:
                n = import_rabobank_csv(str(f))
                total += n
                st.write(f"  `{f.name}` → {n} nieuwe transacties")
            st.success(f"Totaal {total} transacties geïmporteerd.")
            st.rerun()
    else:
        st.info(f"Geen bestanden gevonden in `{BANK_DIR}`")

st.divider()

# ── Transaction list ───────────────────────────────────────────────────────────
df = get_bank_transactions(jaar, kw_num, only_unmatched)
df = df[df["rekening"].isin(ZAKELIJK_IBANS)] if not df.empty else df

if df.empty:
    st.info("Geen transacties gevonden. Importeer eerst een CAMT.053 bestand.")
    st.stop()

matched = df["expense_id"].notna() | df["income_id"].notna()
is_prive = df.get("prive", pd.Series(0, index=df.index)).astype(bool)
n_matched = matched.sum()
n_prive = is_prive.sum()
n_total = len(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Transacties", n_total)
c2.metric("Gekoppeld", int(n_matched))
c3.metric("Privé onttrekking", int(n_prive))
c4.metric("Ongekoppeld", int(n_total - n_matched - n_prive))

st.divider()

# Load expenses and income once for matching suggestions
all_exp = get_expenses(jaar)
all_inc = get_income(jaar)

# ── Per-transaction rows ───────────────────────────────────────────────────────
for _, tx in df.iterrows():
    tx_id = int(tx["id"])
    is_matched = pd.notna(tx.get("expense_id")) or pd.notna(tx.get("income_id"))
    is_prive_tx = bool(tx.get("prive"))
    bedrag = tx["bedrag"]
    bedrag_str = f"€ {bedrag:+,.2f}"

    if is_prive_tx:
        col_status = "🟡"
    elif is_matched:
        col_status = "🟢"
    elif bedrag < 0:
        col_status = "🔴"
    else:
        col_status = "🔵"
    label = f"{col_status} {tx['datum']}  {bedrag_str}  —  {tx['naam']}"
    if is_prive_tx and tx.get("prive_omschrijving"):
        label += f"  *(privé: {tx['prive_omschrijving']})*"
    elif tx.get("fooi") and tx["fooi"] != 0:
        label += f"  *(fooi: € {tx['fooi']:.2f})*"

    with st.expander(label, expanded=False):
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f"**Naam:** {tx['naam']}")
            st.markdown(f"**IBAN:** {tx['iban'] or '—'}")
            st.markdown(f"**Referentie:** {tx['referentie'] or '—'}")
            st.markdown(f"**Bedrag:** {bedrag_str} &nbsp; {'(Betaling)' if bedrag < 0 else '(Ontvangst)'}")
            if tx.get("fooi") and tx["fooi"] != 0:
                st.markdown(f"**Fooi/privé:** € {tx['fooi']:.2f}")

        with c2:
            if is_prive_tx:
                omschr = tx.get("prive_omschrijving") or ""
                st.warning(f"\U0001f7e1 Priv\u00e9 onttrekking: **{omschr or '\u2014'}**")
                if st.button("\U0001f513 Ontkoppelen", key=f"unlink_{tx_id}"):
                    unlink_bank_transaction(tx_id)
                    st.rerun()
            elif is_matched:
                if pd.notna(tx.get("expense_id")):
                    matched_row = all_exp[all_exp["id"] == tx["expense_id"]]
                    if not matched_row.empty:
                        r = matched_row.iloc[0]
                        st.success(f"Gekoppeld aan uitgave: **{r['naam']}** (€ {r['total']:.2f})")
                if pd.notna(tx.get("income_id")):
                    matched_row = all_inc[all_inc["id"] == tx["income_id"]]
                    if not matched_row.empty:
                        r = matched_row.iloc[0]
                        st.success(f"Gekoppeld aan inkomst: **{r['naam']}** (€ {r['total']:.2f})")
                if st.button("🔓 Ontkoppelen", key=f"unlink_{tx_id}"):
                    unlink_bank_transaction(tx_id)
                    st.rerun()
            else:
                # Matching form
                st.markdown("**Koppel aan:**")
                match_type = st.radio(
                    "Type",
                    ["Uitgave", "Inkomst", "Privé onttrekking"],
                    key=f"type_{tx_id}",
                    horizontal=True,
                )

                if match_type == "Privé onttrekking":
                    omschr = st.text_input(
                        "Omschrijving (optioneel)",
                        value="Privé onttrekking" if bedrag < 0 else "Privé storting",
                        key=f"prive_omschr_{tx_id}",
                    )
                    if st.button("\U0001f7e1 Markeer als Privé", key=f"prive_{tx_id}", type="primary"):
                        mark_bank_as_prive(tx_id, omschr)
                        st.rerun()

                elif match_type == "Uitgave" and not all_exp.empty:
                    amt = abs(bedrag)
                    tx_datum_val = tx["datum"] if hasattr(tx["datum"], "year") else None
                    tx_naam_val = str(tx.get("naam") or "")
                    tx_ref_val = str(tx.get("referentie") or "")

                    scored = []
                    for _, er in all_exp.iterrows():
                        s = _score_expense(er, amt, tx_datum_val, tx_naam_val, tx_ref_val)
                        if s >= 0:
                            scored.append((s, er))
                    scored.sort(key=lambda x: -x[0])
                    candidates_rows = [r for _, r in scored[:8]]

                    if not candidates_rows:
                        st.info("Geen passende uitgaven gevonden (datum, bedrag of naam komen niet overeen).")
                    else:
                        candidates = pd.DataFrame(candidates_rows)
                        options = {
                            f"{r['datum']} — {r['naam']} (€ {r['total']:.2f})": int(r["id"])
                            for _, r in candidates.iterrows()
                        }
                        selected_label = st.selectbox(
                            "Kies uitgave",
                            options=list(options.keys()),
                            key=f"sel_exp_{tx_id}",
                        )
                        selected_id = options[selected_label]
                        selected_row = all_exp[all_exp["id"] == selected_id].iloc[0]
                        selected_total = float(selected_row["total"])

                        diff = round(abs(bedrag) - selected_total, 2)
                        fooi_val = 0.0
                        if diff > 0:
                            st.warning(
                                f"Banktransactie is € {diff:.2f} hoger dan de factuur. "
                                f"Dit kan een fooi of privé-deel zijn."
                            )
                            fooi_val = st.number_input(
                                "Fooi / privé bedrag (€)",
                                min_value=0.0,
                                max_value=float(abs(bedrag)),
                                value=diff,
                                step=0.01,
                                key=f"fooi_{tx_id}",
                            )

                        if st.button("✅ Koppelen", key=f"link_exp_{tx_id}", type="primary"):
                            link_bank_transaction(tx_id, expense_id=selected_id, fooi=fooi_val)
                            st.rerun()

                elif match_type == "Inkomst" and not all_inc.empty:
                    amt = abs(bedrag)
                    tx_datum_val = tx["datum"] if hasattr(tx["datum"], "year") else None
                    tx_naam_val = str(tx.get("naam") or "")
                    tx_ref_val = str(tx.get("referentie") or "")

                    scored = []
                    for _, ir in all_inc.iterrows():
                        s = _score_income(ir, amt, tx_datum_val, tx_naam_val, tx_ref_val)
                        if s >= 0:
                            scored.append((s, ir))
                    scored.sort(key=lambda x: -x[0])
                    candidates_rows = [r for _, r in scored[:8]]

                    if not candidates_rows:
                        st.info("Geen passende inkomsten gevonden.")
                    else:
                        candidates = pd.DataFrame(candidates_rows)
                        options = {
                            f"{r['datum']} — {r['naam']} (€ {r['total']:.2f})": int(r["id"])
                            for _, r in candidates.iterrows()
                        }
                        selected_label = st.selectbox(
                            "Kies inkomst",
                            options=list(options.keys()),
                            key=f"sel_inc_{tx_id}",
                        )
                        selected_id = options[selected_label]

                        if st.button("✅ Koppelen", key=f"link_inc_{tx_id}", type="primary"):
                            link_bank_transaction(tx_id, income_id=selected_id)
                            st.rerun()
                else:
                    st.info("Geen uitgaven/inkomsten beschikbaar voor dit jaar.")
