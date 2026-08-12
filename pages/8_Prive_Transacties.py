import streamlit as st
import pandas as pd
import altair as alt
from dateutil.relativedelta import relativedelta
from db import (
    init_db, get_prive_spending,
    set_prive_categorie, set_prive_categorie_by_naam, set_prive_recurring,
    set_prive_recurring_by_naam,
    get_rekeningen, get_schulden, save_schulden, FREQUENTIES,
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
toon_inactief_schulden = st.sidebar.checkbox("Toon afgeloste schulden", value=False)

# ── Load all transactions (in + out) ─────────────────────────────────────────

all_df = get_prive_spending(jaar, maand, rekening_filter, only_costs=False)
all_df_year = get_prive_spending(jaar, None, rekening_filter, only_costs=False)
schulden_df = get_schulden(only_actief=not toon_inactief_schulden)

if all_df.empty:
    st.info("Geen transacties gevonden.")
    st.stop()

df_out = all_df[all_df["bedrag"] < 0].copy()
df_in  = all_df[all_df["bedrag"] > 0].copy()

def _recurring_mask(df: pd.DataFrame) -> pd.Series:
    if "is_recurring" not in df.columns:
        return pd.Series(False, index=df.index)
    return pd.to_numeric(df["is_recurring"], errors="coerce").fillna(0).astype(int).eq(1)

# ── Top totals ────────────────────────────────────────────────────────────────

totaal_uit = df_out["bedrag"].abs().sum()
totaal_in  = df_in["bedrag"].sum()
netto      = totaal_in - totaal_uit

recurring_filtered = df_out[_recurring_mask(df_out)]
recurring_totaal = recurring_filtered["bedrag"].abs().sum() if not recurring_filtered.empty else 0.0

recurring_year_out = all_df_year[(all_df_year["bedrag"] < 0) & _recurring_mask(all_df_year)].copy()
if not recurring_year_out.empty:
    recurring_year_out["maand"] = pd.to_datetime(recurring_year_out["datum"], errors="coerce").dt.month
    recurring_total_year = float(recurring_year_out["bedrag"].abs().sum())
    months_available = pd.to_datetime(all_df_year["datum"], errors="coerce").dt.month.dropna().nunique()
    recurring_avg_month = recurring_total_year / months_available if months_available > 0 else 0.0
else:
    recurring_avg_month = 0.0

fmt = lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

totaal_schuld_restant = schulden_df[schulden_df["actief"]]["huidig_restant"].apply(lambda x: float(x or 0)).sum() if not schulden_df.empty else 0.0
maandelijkse_schuld_termijnen = schulden_df[schulden_df["actief"]]["termijn_bedrag"].apply(lambda x: float(x or 0)).sum() if not schulden_df.empty else 0.0

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("💰 Inkomsten", fmt(totaal_in))
c2.metric("💸 Uitgaven", fmt(totaal_uit))
c3.metric("📊 Netto", fmt(netto),
          delta="positief" if netto >= 0 else "tekort",
          delta_color="normal" if netto >= 0 else "inverse")
c4.metric("🔄 Vaste lasten", fmt(recurring_totaal))
c5.metric("📆 Gem. vaste lasten p/m", fmt(recurring_avg_month),
          help="Gemiddelde over maanden met beschikbare terugkerende kosten in de gekozen jaar/rekening selectie.")
c6.metric("🏦 Schuld restant", fmt(totaal_schuld_restant))
c7.metric("📅 Schuld termijnen p/m", fmt(maandelijkse_schuld_termijnen))

st.divider()

# ── Werkelijke uitgaven per categorie (filter-aware) ─────────────────────────

cat_df = (
    df_out[df_out["prive_categorie"].fillna("") != ""]
    .groupby("prive_categorie")["bedrag"].sum().abs()
    .reset_index()
    .rename(columns={"prive_categorie": "categorie", "bedrag": "totaal"})
)

# Split recurring costs into highlighted aggregates.
leningen_totaal = float(
    recurring_filtered[
        recurring_filtered["prive_categorie"].fillna("").str.lower().isin(["lening", "leningen"])
    ]["bedrag"].abs().sum()
)
other_vaste_lasten_totaal = max(0.0, float(recurring_totaal) - leningen_totaal)

special_rows = pd.DataFrame([
    {"categorie": "Vaste lasten", "totaal": float(recurring_totaal), "special_group": "Vaste lasten"},
    {"categorie": "Leningen", "totaal": leningen_totaal, "special_group": "Leningen"},
    {"categorie": "Overig vaste lasten", "totaal": other_vaste_lasten_totaal, "special_group": "Overig vaste lasten"},
])

# Avoid duplicate visual meaning by removing direct lening category bar from base categories.
cat_df = cat_df[~cat_df["categorie"].str.lower().isin(["lening", "leningen"])]
cat_df["special_group"] = ""

chart_df = pd.concat([cat_df, special_rows], ignore_index=True)
chart_df = chart_df.groupby("categorie", as_index=False)["totaal"].sum()
chart_df = chart_df[chart_df["totaal"] > 0].sort_values("totaal", ascending=False)
category_order = chart_df["categorie"].tolist()

special_lookup = {
    "Vaste lasten": "Vaste lasten",
    "Leningen": "Leningen",
    "Overig vaste lasten": "Overig vaste lasten",
}
chart_df["special_group"] = chart_df["categorie"].map(special_lookup).fillna("")

if not chart_df.empty:
    st.caption("Werkelijke uitgaven per categorie")
    color_scale = alt.Scale(
        domain=["Vaste lasten", "Leningen", "Overig vaste lasten", ""],
        range=["#1D4ED8", "#DC2626", "#0F766E", "#9CA3AF"],
    )
    bars = alt.Chart(chart_df).mark_bar().encode(
        x=alt.X("totaal:Q", title="Bedrag"),
        y=alt.Y("categorie:N", sort=category_order, title=None),
        color=alt.Color("special_group:N", scale=color_scale, legend=None),
        tooltip=[alt.Tooltip("categorie:N"), alt.Tooltip("totaal:Q", format=",.2f")],
    )
    labels = bars.mark_text(align="left", dx=4).encode(text=alt.Text("totaal:Q", format=",.0f"))
    st.altair_chart(bars + labels, use_container_width=True)
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


def _on_rec_change(tx_id: int, naam: str) -> None:
    new_rec = bool(st.session_state.get(f"rec_{tx_id}", False))
    set_prive_recurring(tx_id, new_rec)
    n = set_prive_recurring_by_naam(naam, new_rec)
    if n > 1:
        st.toast(f"{n} transacties van '{naam}' {'gemarkeerd als vast' if new_rec else 'niet meer vast'}", icon="🔄")


def _apply_diff(orig_df: pd.DataFrame, diff: dict, drop_cols: list) -> pd.DataFrame:
    """Reconstruct full edited DataFrame from Streamlit data_editor diff dict."""
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


st.session_state["_schulden_orig_pt"] = schulden_df


def _autosave_schulden_pt() -> None:
    diff = st.session_state.get("schulden_editor_pt")
    if not isinstance(diff, dict):
        return
    orig = st.session_state.get("_schulden_orig_pt", pd.DataFrame())
    if orig.empty:
        return
    to_save = _apply_diff(orig, diff, drop_cols=["betaaldag", "resterend", "verwacht_klaar", "huidig_restant"])
    save_schulden(to_save)
    st.toast("Schulden opgeslagen", icon="✅")

# ── Uitgaven ──────────────────────────────────────────────────────────────────

st.subheader("💸 Uitgaven")

col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 1, 1])
filter_naam_out = col_f1.text_input("Naam (bevat)", key="fn_out")
filter_cat_out  = col_f2.selectbox("Categorie", ["Alle"] + [c for c in PRIVE_CATS if c], key="fc_out")
only_uncat      = col_f3.checkbox("Ongecategoriseerd", key="uncat_out")
only_recurring  = col_f4.checkbox("Vaste lasten", key="rec_only_out")

view_out = df_out.copy()
view_out["prive_categorie"] = view_out["prive_categorie"].fillna("")
if filter_naam_out:
    view_out = view_out[view_out["naam"].str.contains(filter_naam_out, case=False, na=False)]
if filter_cat_out != "Alle":
    view_out = view_out[view_out["prive_categorie"] == filter_cat_out]
if only_uncat:
    view_out = view_out[view_out["prive_categorie"] == ""]
if only_recurring:
    view_out = view_out[_recurring_mask(view_out)]

filter_active = bool(filter_naam_out) or filter_cat_out != "Alle" or only_uncat or only_recurring
if filter_active:
    st.info(f"Filter actief — {len(view_out)} van {len(df_out)} transacties zichtbaar")
else:
    st.caption(f"{len(df_out)} transacties")

# ── Pagination — keeps widget count manageable ────────────────────────────────
row_ctrl_col1, row_ctrl_col2 = st.columns([1, 1])
page_size = row_ctrl_col1.selectbox(
    "Rijen per pagina",
    [25, 50, 100],
    index=0,
    key="rows_per_page_out",
)
total_rows = len(view_out)
total_pages = max(1, (total_rows + page_size - 1) // page_size)
current_page = int(st.session_state.get("page_out", 1))
if current_page < 1:
    current_page = 1
if current_page > total_pages:
    current_page = total_pages
page = row_ctrl_col2.number_input(f"Pagina ({current_page}/{total_pages})", min_value=1, max_value=total_pages, value=current_page, step=1,
                        key="page_out",
                        help=f"{total_rows} transacties — {page_size} per pagina")
st.caption(f"Pagina {int(page)}/{total_pages}")
page_df = view_out.iloc[(page - 1) * page_size : page * page_size]

for _, tx in page_df.iterrows():
    tx_id     = int(tx["id"])
    bedrag    = float(tx["bedrag"])
    cat       = str(tx.get("prive_categorie") or "")
    recurring = int(pd.to_numeric(tx.get("is_recurring", 0), errors="coerce") or 0) == 1

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
        eigen_iban = str(tx.get("rekening") or "").strip()
        tegen_iban = str(tx.get("iban") or "").strip()
        if bedrag < 0:
            van_iban = eigen_iban or "—"
            naar_iban = tegen_iban or "—"
        else:
            van_iban = tegen_iban or "—"
            naar_iban = eigen_iban or "—"
        st.caption(f"Van IBAN: {van_iban}")
        st.caption(f"Naar IBAN: {naar_iban}")
        current_idx = PRIVE_CATS.index(cat) if cat in PRIVE_CATS else 0
        st.selectbox(
            "Categorie", PRIVE_CATS, index=current_idx,
            key=f"cat_{tx_id}", on_change=_on_cat_change, args=(tx_id, str(tx["naam"])),
        )
        st.checkbox(
            "🔄 Vaste last (terugkerende betaling)", value=recurring,
            key=f"rec_{tx_id}",
            on_change=_on_rec_change,
            args=(tx_id, str(tx["naam"])),
        )

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

st.divider()

# ── Schulden (verplaatst van Privé Posten) ───────────────────────────────────

st.subheader("💳 Schulden")

if schulden_df.empty:
    st.info("Nog geen schulden ingevoerd.")
else:
    edit_schulden = schulden_df.drop(columns=["id", "betaaldag"], errors="ignore").copy()
    _f = lambda x: float(x or 0)
    edit_schulden["huidig_restant"] = (
        edit_schulden["origineel_bedrag"].apply(_f)
        - edit_schulden["termijn_bedrag"].apply(_f)
        * edit_schulden["betaald_termijnen"].apply(lambda x: int(x or 0))
        - edit_schulden["extra_betaald"].apply(_f)
    ).clip(lower=0).round(2)
    edit_schulden["resterend"] = (
        edit_schulden["aantal_termijnen"].apply(lambda x: int(x or 0))
        - edit_schulden["betaald_termijnen"].apply(lambda x: int(x or 0))
    ).clip(lower=0)

    freq_months = {"maandelijks": 1, "kwartaal": 3, "halfjaar": 6, "jaar": 12}

    def _verwacht_klaar(row) -> str:
        try:
            start = pd.to_datetime(str(row.get("start_datum") or "")).date()
            n_terms = int(row.get("aantal_termijnen") or 0)
            months = freq_months.get(str(row.get("frequentie") or "maandelijks"), 1)
            if n_terms <= 0:
                return ""
            eind = start + relativedelta(months=n_terms * months)
            return eind.strftime("%d-%m-%Y")
        except Exception:
            return ""

    edit_schulden["verwacht_klaar"] = edit_schulden.apply(_verwacht_klaar, axis=1)
    edit_schulden = edit_schulden[[
        "naam", "betaald_termijnen", "aantal_termijnen", "resterend",
        "termijn_bedrag", "origineel_bedrag", "huidig_restant",
        "start_datum", "betaaldatum", "frequentie", "verwacht_klaar",
    ]]

    st.data_editor(
        edit_schulden,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        on_change=_autosave_schulden_pt,
        column_config={
            "naam":              st.column_config.TextColumn("Naam", width="medium"),
            "betaald_termijnen": st.column_config.NumberColumn("Betaald", min_value=0, width="small"),
            "aantal_termijnen":  st.column_config.NumberColumn("Totaal termijnen", min_value=0, width="small"),
            "resterend":         st.column_config.NumberColumn("Resterend", min_value=0, width="small", disabled=True),
            "termijn_bedrag":    st.column_config.NumberColumn("Termijn bedrag", format="€ %.2f", width="small"),
            "origineel_bedrag":  st.column_config.NumberColumn("Origineel bedrag", format="€ %.2f", width="small"),
            "huidig_restant":    st.column_config.NumberColumn("Huidig restant", format="€ %.2f", width="small", disabled=True),
            "start_datum":       st.column_config.DateColumn("Startdatum", format="DD-MM-YYYY", width="small"),
            "betaaldatum":       st.column_config.DateColumn("Volgende betaling", format="DD-MM-YYYY", width="small"),
            "frequentie":        st.column_config.SelectboxColumn("Frequentie", options=FREQUENTIES, width="small"),
            "verwacht_klaar":    st.column_config.TextColumn("Verwacht klaar", width="small", disabled=True),
        },
        key="schulden_editor_pt",
    )
