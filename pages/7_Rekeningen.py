import streamlit as st
import pandas as pd
from pathlib import Path
from db import (
    init_db, get_rekeningen, save_rekeningen, upsert_rekening,
    import_camt, import_rabobank_csv, get_bank_transactions,
)

st.set_page_config(page_title="Rekeningen", page_icon="🏦", layout="wide")
init_db()

BANK_DIR = Path("data/BankTransactions")

# Pre-populate known accounts on first run
def _seed_rekeningen():
    upsert_rekening("Greenlight-IT Zakelijk",  "NL84RABO0188971130", "zakelijk", "betaalrekening")
    upsert_rekening("Privé Betaalrekening",     "NL59RABO0154107840", "prive",    "betaalrekening")
    upsert_rekening("Privé Spaarrekening",      "NL86RABO3500294723", "prive",    "spaarrekening")

_seed_rekeningen()

st.title("🏦 Rekeningen & Saldo")

# ── Import ────────────────────────────────────────────────────────────────────

with st.expander("📥 Importeer banktransacties", expanded=False):
    st.caption(
        "XML-bestanden (CAMT.053) en CSV-bestanden (Rabobank) uit "
        f"`{BANK_DIR}` worden geïmporteerd."
    )
    if st.button("Importeer alle bestanden"):
        results = []
        for f in sorted(BANK_DIR.glob("*.xml")):
            try:
                n = import_camt(str(f))
                results.append(f"✅ {f.name}: {n} nieuwe transacties (CAMT)")
            except Exception as e:
                results.append(f"❌ {f.name}: {e}")
        for f in sorted(BANK_DIR.glob("*.csv")):
            try:
                n = import_rabobank_csv(str(f))
                results.append(f"✅ {f.name}: {n} nieuwe transacties (CSV)")
            except Exception as e:
                results.append(f"❌ {f.name}: {e}")
        if results:
            for r in results:
                st.write(r)
        else:
            st.info("Geen bestanden gevonden.")
        st.rerun()

st.divider()

# ── Metrics ───────────────────────────────────────────────────────────────────

rek_df = get_rekeningen()

fmt = lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

if not rek_df.empty:
    col_z, col_p = st.columns(2)

    for col, type_label, title in [
        (col_z, "zakelijk", "💼 Zakelijk"),
        (col_p, "prive",    "🏠 Privé"),
    ]:
        subset = rek_df[rek_df["type"] == type_label]
        totaal_type = subset["saldo"].sum()
        with col:
            with st.container(border=True):
                st.metric(title, fmt(totaal_type))
                for _, r in subset.iterrows():
                    label = "💰 " if r["categorie"] == "spaarrekening" else "🏦 "
                    st.caption(f"{label}{r['naam']}: **{fmt(r['saldo'])}**")

st.divider()

# ── Rekeningen editor ─────────────────────────────────────────────────────────

st.subheader("Rekeningen")
st.caption("Pas het saldo handmatig aan na elke bankmutatie; later wordt dit berekend uit de transacties.")

st.session_state["_rek_orig"] = rek_df


def _autosave_rek():
    diff = st.session_state.get("rek_editor")
    if not isinstance(diff, dict):
        return
    orig = st.session_state.get("_rek_orig", pd.DataFrame())
    if orig.empty:
        return
    base = orig.drop(columns=["id"], errors="ignore").copy()
    deleted = set(diff.get("deleted_rows", []))
    for idx_str, changes in diff.get("edited_rows", {}).items():
        for col, val in changes.items():
            if col in base.columns:
                base.at[int(idx_str), col] = val
    remaining = [i for i in range(len(base)) if i not in deleted]
    result = base.iloc[remaining].reset_index(drop=True)
    orig_ids = orig["id"].iloc[remaining].reset_index(drop=True) if "id" in orig.columns else pd.Series([])
    for new_row in diff.get("added_rows", []):
        result = pd.concat([result, pd.DataFrame([new_row])], ignore_index=True)
        orig_ids = pd.concat([orig_ids, pd.Series([None])], ignore_index=True)
    result.insert(0, "id", orig_ids)
    save_rekeningen(result)
    st.toast("Rekeningen opgeslagen", icon="✅")


edit_rek = rek_df.drop(columns=["id"], errors="ignore").copy()
if "laatste_update" in edit_rek.columns:
    from db import _to_date as _td
    edit_rek["laatste_update"] = edit_rek["laatste_update"].apply(_td)
st.data_editor(
    edit_rek,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    on_change=_autosave_rek,
    column_config={
        "naam":           st.column_config.TextColumn("Naam", width="medium"),
        "iban":           st.column_config.TextColumn("IBAN", width="medium"),
        "type":           st.column_config.SelectboxColumn("Type", options=["zakelijk", "prive"], width="small"),
        "categorie":      st.column_config.SelectboxColumn("Categorie",
                              options=["betaalrekening", "spaarrekening"], width="small"),
        "saldo":          st.column_config.NumberColumn("Saldo", format="€ %.2f", width="small"),
        "laatste_update": st.column_config.DateColumn("Laatste update", format="DD-MM-YYYY", width="small"),
    },
    key="rek_editor",
)

st.divider()

# ── Transaction count per rekening ────────────────────────────────────────────

st.subheader("Transacties per rekening")
jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024])

if not rek_df.empty:
    rows = []
    for _, r in rek_df.iterrows():
        txdf = get_bank_transactions(jaar, rekening=r["iban"])
        matched   = int(((txdf["expense_id"].notna()) | (txdf["income_id"].notna())).sum()) if not txdf.empty else 0
        prive_cnt = int(txdf["prive"].sum()) if not txdf.empty else 0
        total_cnt = len(txdf)
        rows.append({
            "Rekening":    r["naam"],
            "IBAN":        r["iban"],
            "Transacties": total_cnt,
            "Gekoppeld":   matched,
            "Privé":       prive_cnt,
            "Ongekoppeld": total_cnt - matched - prive_cnt,
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
