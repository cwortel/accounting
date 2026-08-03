import streamlit as st
import pandas as pd
from db import (
    init_db, get_schulden, save_schulden,
    get_vaste_lasten, save_vaste_lasten,
    monthly_equivalent, FREQUENTIES,
)

st.set_page_config(page_title="Schulden & Vaste Lasten", page_icon="💳", layout="wide")
init_db()

st.title("💳 Schulden & Vaste Lasten")

# ── Sidebar ───────────────────────────────────────────────────────────────────

toon_inactief = st.sidebar.checkbox("Toon afgeloste schulden", value=False)

# ── Metrics ───────────────────────────────────────────────────────────────────

schulden_df = get_schulden(only_actief=not toon_inactief)
vaste_df = get_vaste_lasten(only_actief=True)

maandelijks_schulden = schulden_df[schulden_df["actief"]]["termijn_bedrag"].apply(
    lambda x: float(x or 0)
).sum() if not schulden_df.empty else 0.0

maandelijks_vaste = vaste_df.apply(
    lambda r: monthly_equivalent(float(r.get("bedrag") or 0), str(r.get("frequentie") or "maandelijks")),
    axis=1,
).sum() if not vaste_df.empty else 0.0

totaal_restant = schulden_df[schulden_df["actief"]]["huidig_restant"].apply(
    float
).sum() if not schulden_df.empty else 0.0

c1, c2, c3 = st.columns(3)
c1.metric("Totaal restant schulden", f"€ {totaal_restant:,.0f}".replace(",", "."))
c2.metric("Maandelijkse schuld termijnen", f"€ {maandelijks_schulden:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c3.metric("Maandelijkse vaste lasten", f"€ {maandelijks_vaste:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.divider()

# ── Schulden editor ───────────────────────────────────────────────────────────

st.subheader("Schulden")

def _apply_diff(orig_df: pd.DataFrame, diff: dict, drop_cols: list) -> pd.DataFrame:
    """Reconstruct the full edited DataFrame from data_editor's diff dict."""
    base = orig_df.drop(columns=["id"] + drop_cols, errors="ignore").copy()
    deleted = set(diff.get("deleted_rows", []))
    for idx_str, changes in diff.get("edited_rows", {}).items():
        for col, val in changes.items():
            if col in base.columns:
                base.at[int(idx_str), col] = val
    remaining_idx = [i for i in range(len(base)) if i not in deleted]
    result = base.iloc[remaining_idx].reset_index(drop=True)
    orig_ids = orig_df["id"].iloc[remaining_idx].reset_index(drop=True) if "id" in orig_df.columns else pd.Series([])
    for new_row in diff.get("added_rows", []):
        result = pd.concat([result, pd.DataFrame([new_row])], ignore_index=True)
        orig_ids = pd.concat([orig_ids, pd.Series([None])], ignore_index=True)
    result.insert(0, "id", orig_ids)
    return result


# Store originals in session state so callbacks can restore IDs
st.session_state["_schulden_orig"] = schulden_df


def _autosave_schulden():
    diff = st.session_state.get("schulden_editor")
    if not isinstance(diff, dict):
        return
    orig = st.session_state.get("_schulden_orig", pd.DataFrame())
    if orig.empty:
        return
    to_save = _apply_diff(orig, diff, drop_cols=["betaaldag"])
    save_schulden(to_save)
    st.toast("Schulden opgeslagen", icon="✅")


edit_schulden = schulden_df.drop(columns=["id", "betaaldag"], errors="ignore").copy()
# Pre-compute so the disabled column shows the correct derived value
_f = lambda x: float(x or 0)
edit_schulden["huidig_restant"] = (
    edit_schulden["origineel_bedrag"].apply(_f)
    - edit_schulden["termijn_bedrag"].apply(_f)
    * edit_schulden["betaald_termijnen"].apply(lambda x: int(x or 0))
    - edit_schulden["extra_betaald"].apply(_f)
).clip(lower=0).round(2)
edit_schulden = edit_schulden[[
    "naam", "betaald_termijnen", "aantal_termijnen", "termijn_bedrag",
    "extra_betaald", "origineel_bedrag", "huidig_restant",
    "start_datum", "betaaldatum", "frequentie",
    "partij", "iban", "notities", "actief",
]]
edited_s = st.data_editor(
    edit_schulden,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    on_change=_autosave_schulden,
    column_config={
        "naam":              st.column_config.TextColumn("Naam", width="medium"),
        "partij":            st.column_config.TextColumn("Partij / Schuldeiser", width="medium"),
        "iban":              st.column_config.TextColumn("IBAN", width="medium"),
        "origineel_bedrag":  st.column_config.NumberColumn("Origineel bedrag", format="€ %.2f", width="small"),
        "huidig_restant":    st.column_config.NumberColumn("Huidig restant", format="€ %.2f", width="small", disabled=True),
        "termijn_bedrag":    st.column_config.NumberColumn("Termijn bedrag", format="€ %.2f", width="small"),
        "frequentie":        st.column_config.SelectboxColumn("Frequentie", options=FREQUENTIES, width="small"),
        "start_datum":       st.column_config.DateColumn("Startdatum", format="DD-MM-YYYY", width="small"),
        "aantal_termijnen":  st.column_config.NumberColumn("Totaal termijnen", min_value=0, width="small"),
        "betaald_termijnen": st.column_config.NumberColumn("Betaald", min_value=0, width="small"),
        "extra_betaald":     st.column_config.NumberColumn("Extra aflossing", format="€ %.2f", width="small",
                                                            help="Cumulatief extra bedrag buiten de reguliere termijnen"),
        "huidig_restant":    st.column_config.NumberColumn("Huidig restant", format="€ %.2f", width="small", disabled=True),
        "betaaldatum":       st.column_config.DateColumn("Volgende betaling", format="DD-MM-YYYY", width="small"),
        "actief":            st.column_config.CheckboxColumn("Actief", width="small"),
        "notities":          st.column_config.TextColumn("Notities", width="large"),
    },
    key="schulden_editor",
)

# Show computed remaining termijnen and projected end date
if not schulden_df.empty:
    actief_met_termijnen = schulden_df[
        schulden_df["actief"] & (schulden_df["aantal_termijnen"] > 0)
    ].copy()
    if not actief_met_termijnen.empty:
        import math
        from dateutil.relativedelta import relativedelta
        freq_months = {"maandelijks": 1, "kwartaal": 3, "halfjaar": 6, "jaar": 12}
        rows_proj = []
        for _, r in actief_met_termijnen.iterrows():
            resterend = max(0, int(r["aantal_termijnen"]) - int(r["betaald_termijnen"]))
            freq = freq_months.get(str(r.get("frequentie") or "maandelijks"), 1)
            try:
                start = pd.to_datetime(str(r["start_datum"])).date()
                eind = start + relativedelta(months=int(r["aantal_termijnen"]) * freq)
                eind_str = eind.strftime("%b %Y")
            except Exception:
                eind_str = "–"
            rows_proj.append({
                "Schuld": r["naam"],
                "Betaald": f"{int(r['betaald_termijnen'])} / {int(r['aantal_termijnen'])}",
                "Resterend": resterend,
                "Verwacht klaar": eind_str,
            })
        st.dataframe(pd.DataFrame(rows_proj), hide_index=True, use_container_width=True)

st.divider()

# ── Vaste lasten editor ───────────────────────────────────────────────────────

st.subheader("Vaste Lasten")
st.caption("Terugkerende maandelijkse en periodieke kosten")

alle_vaste_df = get_vaste_lasten(only_actief=False)
st.session_state["_vaste_orig"] = alle_vaste_df


def _autosave_vaste():
    diff = st.session_state.get("vaste_editor")
    if not isinstance(diff, dict):
        return
    orig = st.session_state.get("_vaste_orig", pd.DataFrame())
    if orig.empty:
        return
    to_save = _apply_diff(orig, diff, drop_cols=["betaaldag"])
    save_vaste_lasten(to_save)
    st.toast("Vaste lasten opgeslagen", icon="✅")


edit_vaste = alle_vaste_df.drop(columns=["id", "betaaldag"], errors="ignore")

VASTE_CATS = ["Wonen", "Verzekering", "Belasting", "Abonnement", "Opleiding", "Overig"]

edited_v = st.data_editor(
    edit_vaste,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    on_change=_autosave_vaste,
    column_config={
        "naam":       st.column_config.TextColumn("Naam", width="medium"),
        "partij":     st.column_config.TextColumn("Partij", width="medium"),
        "iban":       st.column_config.TextColumn("IBAN", width="medium"),
        "bedrag":     st.column_config.NumberColumn("Bedrag", format="€ %.2f", width="small"),
        "frequentie": st.column_config.SelectboxColumn("Frequentie", options=FREQUENTIES, width="small"),
        "betaaldatum":st.column_config.DateColumn("Volgende betaling", format="DD-MM-YYYY", width="small"),
        "categorie":  st.column_config.SelectboxColumn("Categorie", options=VASTE_CATS, width="small"),
        "actief":     st.column_config.CheckboxColumn("Actief", width="small"),
    },
    key="vaste_editor",
)
