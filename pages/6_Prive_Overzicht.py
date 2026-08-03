import streamlit as st
import pandas as pd
from db import (
    init_db, get_schulden, get_vaste_lasten,
    get_prive_inkomsten, save_prive_inkomsten,
    monthly_equivalent,
)

st.set_page_config(page_title="Privé Overzicht", page_icon="🏠", layout="wide")
init_db()

st.title("🏠 Privé Overzicht")

MAANDEN = {
    1: "Januari", 2: "Februari", 3: "Maart", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Augustus",
    9: "September", 10: "Oktober", 11: "November", 12: "December",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024])
maand_label = st.sidebar.selectbox("Maand", list(MAANDEN.values()), index=7)  # Augustus default
maand = [k for k, v in MAANDEN.items() if v == maand_label][0]

# ── Inkomsten editor ──────────────────────────────────────────────────────────

st.subheader("Inkomsten")
st.caption("Netto privé inkomsten deze maand (bijv. privé onttrekking, salaris partner)")

ink_df = get_prive_inkomsten(jaar, maand)
edit_ink = ink_df[["naam", "bedrag"]].copy() if not ink_df.empty else pd.DataFrame(
    [{"naam": "Privé onttrekking", "bedrag": 0.0}]
)

st.session_state["_ink_jaar_maand"] = (jaar, maand)
st.session_state["_ink_orig"] = edit_ink


def _autosave_inkomsten():
    diff = st.session_state.get("ink_editor")
    if not isinstance(diff, dict):
        return
    j, m = st.session_state.get("_ink_jaar_maand", (jaar, maand))
    orig = st.session_state.get("_ink_orig", pd.DataFrame(columns=["naam", "bedrag"]))
    base = orig[["naam", "bedrag"]].copy()
    deleted = set(diff.get("deleted_rows", []))
    for idx_str, changes in diff.get("edited_rows", {}).items():
        for col, val in changes.items():
            if col in base.columns:
                base.at[int(idx_str), col] = val
    remaining = [i for i in range(len(base)) if i not in deleted]
    result = base.iloc[remaining].reset_index(drop=True)
    for new_row in diff.get("added_rows", []):
        result = pd.concat([result, pd.DataFrame([new_row])], ignore_index=True)
    save_prive_inkomsten(result, j, m)
    st.toast("Inkomsten opgeslagen", icon="✅")


edited_ink = st.data_editor(
    edit_ink,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    on_change=_autosave_inkomsten,
    column_config={
        "naam":   st.column_config.TextColumn("Omschrijving", width="large"),
        "bedrag": st.column_config.NumberColumn("Bedrag", format="€ %.2f", width="small"),
    },
    key="ink_editor",
)

totaal_inkomsten = edited_ink["bedrag"].apply(lambda x: float(x or 0)).sum()

st.divider()

# ── Vaste lasten overzicht ────────────────────────────────────────────────────

st.subheader("Vaste Lasten")
st.caption("Uit de Schulden & Vaste Lasten pagina — bewerken kan daar")

vaste_df = get_vaste_lasten(only_actief=True)

if vaste_df.empty:
    st.info("Nog geen vaste lasten ingevoerd. Ga naar **Schulden & Vaste Lasten** om ze toe te voegen.")
    maandelijks_vaste = 0.0
else:
    vaste_df["p/m"] = vaste_df.apply(
        lambda r: monthly_equivalent(float(r.get("bedrag") or 0), str(r.get("frequentie") or "maandelijks")),
        axis=1,
    )
    disp_vaste = vaste_df[["naam", "bedrag", "frequentie", "betaaldatum", "categorie", "p/m"]].copy()
    disp_vaste = disp_vaste.rename(columns={
        "naam": "Naam", "bedrag": "Bedrag", "frequentie": "Frequentie",
        "betaaldatum": "Volgende betaling", "categorie": "Categorie", "p/m": "p/m equivalent",
    })
    st.dataframe(
        disp_vaste,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Bedrag":           st.column_config.NumberColumn(format="€ %.2f"),
            "Volgende betaling": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "p/m equivalent":   st.column_config.NumberColumn(format="€ %.2f"),
        },
    )
    maandelijks_vaste = vaste_df["p/m"].sum()

st.divider()

# ── Schulden termijnen ────────────────────────────────────────────────────────

st.subheader("Schulden termijnen")
st.caption("Actieve aflosverplichtingen — bewerken via Schulden & Vaste Lasten")

schulden_df = get_schulden(only_actief=True)

if schulden_df.empty:
    st.info("Nog geen schulden ingevoerd.")
    maandelijks_schulden = 0.0
else:
    schulden_df = schulden_df[schulden_df["termijn_bedrag"] > 0].copy()
    schulden_df["p/m"] = schulden_df.apply(
        lambda r: monthly_equivalent(float(r.get("termijn_bedrag") or 0), str(r.get("frequentie") or "maandelijks")),
        axis=1,
    )
    disp_s = schulden_df[["naam", "partij", "huidig_restant", "termijn_bedrag", "frequentie", "p/m"]].copy()
    disp_s = disp_s.rename(columns={
        "naam": "Schuld", "partij": "Schuldeiser",
        "huidig_restant": "Restant", "termijn_bedrag": "Termijn",
        "frequentie": "Frequentie", "p/m": "p/m equivalent",
    })
    st.dataframe(
        disp_s,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Restant":        st.column_config.NumberColumn(format="€ %.2f"),
            "Termijn":        st.column_config.NumberColumn(format="€ %.2f"),
            "p/m equivalent": st.column_config.NumberColumn(format="€ %.2f"),
        },
    )
    maandelijks_schulden = schulden_df["p/m"].sum()

st.divider()

# ── Saldo ─────────────────────────────────────────────────────────────────────

st.subheader(f"Saldo — {maand_label} {jaar}")

totaal_kosten = maandelijks_vaste + maandelijks_schulden
netto = totaal_inkomsten - totaal_kosten

c1, c2, c3, c4 = st.columns(4)
c1.metric("Inkomsten", f"€ {totaal_inkomsten:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c2.metric("Vaste lasten p/m", f"€ {maandelijks_vaste:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c3.metric("Schuld termijnen p/m", f"€ {maandelijks_schulden:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c4.metric(
    "Netto beschikbaar",
    f"€ {netto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    delta=f"{'positief' if netto >= 0 else 'tekort'}",
    delta_color="normal" if netto >= 0 else "inverse",
)

# ── Breakdown bar ─────────────────────────────────────────────────────────────

if totaal_inkomsten > 0:
    breakdown = pd.DataFrame({
        "Post": ["Vaste lasten", "Schuld termijnen", "Beschikbaar"],
        "Bedrag": [
            maandelijks_vaste,
            maandelijks_schulden,
            max(0.0, netto),
        ],
    }).set_index("Post")
    st.bar_chart(breakdown)
