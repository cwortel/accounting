import streamlit as st
import pandas as pd
import altair as alt
from db import init_db, get_prive_spending, set_prive_categorie, set_prive_categorie_by_naam, get_rekeningen

st.set_page_config(page_title="Privé Transacties", page_icon="🏠", layout="wide")
init_db()

PRIVE_CATS = [
    "",
    "Boodschappen",
    "Uit eten / café",
    "Take away",
    "Transport",
    "Wonen & utilities",
    "Verzekering",
    "Abonnementen",
    "Gezondheid",
    "Kleding",
    "Opleiding",
    "Vrije tijd",
    "Overig",
]

MAANDEN = {
    0: "Alle maanden",
    1: "Januari", 2: "Februari", 3: "Maart", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Augustus",
    9: "September", 10: "Oktober", 11: "November", 12: "December",
}

st.title("🏠 Privé Transacties")

# ── Sidebar ───────────────────────────────────────────────────────────────────

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024])
maand_label = st.sidebar.selectbox("Maand", list(MAANDEN.values()))
maand = [k for k, v in MAANDEN.items() if v == maand_label][0] or None

rek_df = get_rekeningen()
prive_rek = rek_df[rek_df["type"] == "prive"] if not rek_df.empty else pd.DataFrame()
rek_options = {"Alle privé rekeningen": None}
for _, r in prive_rek.iterrows():
    rek_options[r["naam"]] = r["iban"]
rek_label = st.sidebar.selectbox("Rekening", list(rek_options.keys()))
rekening_filter = rek_options[rek_label]

only_uncategorised = st.sidebar.checkbox("Alleen ongecategoriseerd", value=False)

# ── Load transactions ─────────────────────────────────────────────────────────

df = get_prive_spending(jaar, maand, rekening_filter)

if df.empty:
    st.info("Geen transacties gevonden.")
    st.stop()

if only_uncategorised:
    df = df[df["prive_categorie"] == ""]

# ── Spending overview chart ───────────────────────────────────────────────────

cat_df = (
    df[df["prive_categorie"] != ""]
    .groupby("prive_categorie")["bedrag"]
    .sum()
    .abs()
    .reset_index()
    .rename(columns={"prive_categorie": "categorie", "bedrag": "totaal"})
    .sort_values("totaal", ascending=False)
)

n_total = len(df)
n_cat = (df["prive_categorie"] != "").sum()
n_uncat = n_total - n_cat

c1, c2, c3 = st.columns(3)
c1.metric("Transacties", n_total)
c2.metric("Gecategoriseerd", n_cat)
c3.metric("Ongecategoriseerd", n_uncat)

if not cat_df.empty:
    st.divider()
    st.subheader("Uitgaven per categorie")
    bars = alt.Chart(cat_df).mark_bar().encode(
        x=alt.X("totaal:Q", title="Bedrag"),
        y=alt.Y("categorie:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("categorie:N"), alt.Tooltip("totaal:Q", format=",.2f")],
    )
    labels = bars.mark_text(align="left", dx=4).encode(
        text=alt.Text("totaal:Q", format=",.0f")
    )
    st.altair_chart(bars + labels, use_container_width=True)

st.divider()

# ── Transaction list with inline category picker ──────────────────────────────

st.subheader("Transacties")

for _, tx in df.iterrows():
    tx_id = int(tx["id"])
    bedrag = float(tx["bedrag"])
    cat = str(tx.get("prive_categorie") or "")

    label = f"{'🟡' if not cat else '🟢'}  {tx['datum']}  —  **{tx['naam']}**  —  € {abs(bedrag):,.2f}"
    if cat:
        label += f"  *({cat})*"

    with st.expander(label, expanded=False):
        ref = str(tx.get("referentie") or "").strip()
        if ref:
            st.caption(f"📝 {ref}")
        st.caption(f"Rekening: {tx.get('rekening', '')}")

        current_idx = PRIVE_CATS.index(cat) if cat in PRIVE_CATS else 0
        new_cat = st.selectbox(
            "Categorie",
            PRIVE_CATS,
            index=current_idx,
            key=f"cat_{tx_id}",
        )
        if new_cat != cat:
            set_prive_categorie(tx_id, new_cat)
            n = set_prive_categorie_by_naam(str(tx["naam"]), new_cat)
            if n > 0:
                st.toast(f"{n} transacties van '{tx['naam']}' → {new_cat}", icon="✅")
            st.rerun()
