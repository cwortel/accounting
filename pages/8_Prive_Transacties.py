import streamlit as st
import pandas as pd
import altair as alt
from db import (
    init_db, get_prive_spending,
    set_prive_categorie, set_prive_categorie_by_naam, set_prive_recurring,
    get_rekeningen,
)

st.set_page_config(page_title="Privé Transacties", page_icon="🏠", layout="wide")
init_db()

PRIVE_CATS = [
    "",
    "Boodschappen",
    "Cash opname",
    "Aanvulling Creditcard",
    "Uit eten / café",
    "Take away",
    "Transport",
    "Wonen & utilities",
    "Verzekering",
    "Abonnementen",
    "Bank kosten",
    "Gezondheid",
    "Gezamenlijke rekening",
    "Hypotheek",
    "Kleding",
    "Lening",
    "Opleiding",
    "Vrije tijd",
    "Vakantie",
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

# ── Load all transactions (in + out) ─────────────────────────────────────────

all_df = get_prive_spending(jaar, maand, rekening_filter, only_costs=False)

if all_df.empty:
    st.info("Geen transacties gevonden.")
    st.stop()

df_out = all_df[all_df["bedrag"] < 0].copy()
df_in  = all_df[all_df["bedrag"] > 0].copy()

# ── Top totals ────────────────────────────────────────────────────────────────

totaal_uit = df_out["bedrag"].abs().sum()
totaal_in  = df_in["bedrag"].sum()
netto      = totaal_in - totaal_uit
fmt = lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

c1, c2, c3 = st.columns(3)
c1.metric("💰 Inkomsten", fmt(totaal_in))
c2.metric("💸 Uitgaven", fmt(totaal_uit))
c3.metric("📊 Netto", fmt(netto),
          delta="positief" if netto >= 0 else "tekort",
          delta_color="normal" if netto >= 0 else "inverse")

st.divider()

# ── Callback for category change ──────────────────────────────────────────────

def _on_cat_change(tx_id: int, naam: str) -> None:
    new_cat = st.session_state.get(f"cat_{tx_id}", "")
    set_prive_categorie(tx_id, new_cat)
    if new_cat:
        n = set_prive_categorie_by_naam(naam, new_cat)
        if n > 1:
            st.toast(f"{n} transacties van '{naam}' → {new_cat}", icon="✅")
    else:
        st.toast("Categorie verwijderd", icon="🗑️")

# ── Uitgaven ──────────────────────────────────────────────────────────────────

st.subheader("💸 Uitgaven")

col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
filter_naam_out = col_f1.text_input("Naam (bevat)", key="fn_out")
filter_cat_out  = col_f2.selectbox("Categorie", ["Alle"] + [c for c in PRIVE_CATS if c], key="fc_out")
only_uncat      = col_f3.checkbox("Ongecategoriseerd", key="uncat_out")

view_out = df_out.copy()
view_out["prive_categorie"] = view_out["prive_categorie"].fillna("")
if filter_naam_out:
    view_out = view_out[view_out["naam"].str.contains(filter_naam_out, case=False, na=False)]
if filter_cat_out != "Alle":
    view_out = view_out[view_out["prive_categorie"] == filter_cat_out]
if only_uncat:
    view_out = view_out[view_out["prive_categorie"] == ""]

filter_active = bool(filter_naam_out) or filter_cat_out != "Alle" or only_uncat
if filter_active:
    st.info(f"Filter actief — {len(view_out)} van {len(df_out)} transacties zichtbaar")
else:
    st.caption(f"{len(df_out)} transacties")

# Chart always reflects full unfiltered spending, shown after the list
cat_df = (
    df_out[df_out["prive_categorie"].fillna("") != ""]
    .groupby("prive_categorie")["bedrag"].sum().abs()
    .reset_index()
    .rename(columns={"prive_categorie": "categorie", "bedrag": "totaal"})
    .sort_values("totaal", ascending=False)
)

# ── Pagination — keeps widget count manageable ────────────────────────────────
PAGE_SIZE = 25
total_rows = len(view_out)
total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)
page = st.number_input("Pagina", min_value=1, max_value=total_pages, value=1, step=1,
                        key="page_out",
                        help=f"{total_rows} transacties — {PAGE_SIZE} per pagina")
page_df = view_out.iloc[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

for _, tx in page_df.iterrows():
    tx_id     = int(tx["id"])
    bedrag    = float(tx["bedrag"])
    cat       = str(tx.get("prive_categorie") or "")
    recurring = bool(tx.get("is_recurring", 0))

    icon  = "🔄" if recurring else ("🟡" if not cat else "🟢")
    label = f"{icon}  {tx['datum']}  —  **{tx['naam']}**  —  {fmt(abs(bedrag))}"
    if cat:
        label += f"  *({cat})*"
    if recurring:
        label += "  *(vaste last)*"

    with st.expander(label, expanded=False):
        ref = str(tx.get("referentie") or "").strip()
        if ref:
            st.caption(f"📝 {ref}")
        st.caption(f"Rekening: {tx.get('rekening', '')}")
        current_idx = PRIVE_CATS.index(cat) if cat in PRIVE_CATS else 0
        st.selectbox(
            "Categorie", PRIVE_CATS, index=current_idx,
            key=f"cat_{tx_id}", on_change=_on_cat_change, args=(tx_id, str(tx["naam"])),
        )
        st.checkbox(
            "🔄 Vaste last (terugkerende betaling)", value=recurring,
            key=f"rec_{tx_id}",
            on_change=lambda tid=tx_id: set_prive_recurring(
                tid, st.session_state.get(f"rec_{tid}", False)
            ),
        )

if not cat_df.empty:
    st.divider()
    st.caption("Uitgaven per categorie (alle transacties)")
    bars = alt.Chart(cat_df).mark_bar().encode(
        x=alt.X("totaal:Q", title="Bedrag"),
        y=alt.Y("categorie:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("categorie:N"), alt.Tooltip("totaal:Q", format=",.2f")],
    )
    labels = bars.mark_text(align="left", dx=4).encode(text=alt.Text("totaal:Q", format=",.0f"))
    st.altair_chart(bars + labels, use_container_width=True)

st.divider()

# ── Inkomsten ─────────────────────────────────────────────────────────────────

st.subheader(f"💰 Inkomsten  ({len(df_in)})")

filter_naam_in = st.text_input("Naam (bevat)", key="fn_in")
view_in = df_in.copy()
if filter_naam_in:
    view_in = view_in[view_in["naam"].str.contains(filter_naam_in, case=False, na=False)]

st.dataframe(
    view_in[["datum", "naam", "bedrag", "referentie", "rekening"]].rename(columns={
        "datum": "Datum", "naam": "Naam", "bedrag": "Bedrag",
        "referentie": "Omschrijving", "rekening": "Rekening",
    }),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Datum":  st.column_config.DateColumn(format="DD-MM-YYYY"),
        "Bedrag": st.column_config.NumberColumn(format="€ %.2f"),
    },
)
