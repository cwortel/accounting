import streamlit as st
import pandas as pd
from db import init_db, get_income, save_income, get_expenses, save_expenses, get_categories

st.set_page_config(page_title="Overzicht", page_icon="📊", layout="wide")
init_db()

st.title("📊 Overzicht Boekhouding")

# ── Shared controls ───────────────────────────────────────────────────────────

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024], key="jaar")
kw_label = st.sidebar.selectbox("Kwartaal", ["Alle", "Q1", "Q2", "Q3", "Q4"])
kw_num = None if kw_label == "Alle" else int(kw_label[1])

categories = get_categories()

# ── Load data ─────────────────────────────────────────────────────────────────

inc_df = get_income(jaar, kw_num)
exp_df = get_expenses(jaar, kw_num)

# ── Summary metrics ───────────────────────────────────────────────────────────

omzet    = float(inc_df["ex_btw"].sum()) if not inc_df.empty else 0.0
kosten   = float(exp_df["ex_btw"].sum()) if not exp_df.empty else 0.0
btw_in   = float(inc_df["btw"].sum())    if not inc_df.empty else 0.0
btw_uit  = float(exp_df["btw"].sum())    if not exp_df.empty else 0.0
winst    = omzet - kosten
btw_sal  = btw_in - btw_uit

c1, c2, c3, c4 = st.columns(4)
c1.metric("Omzet (ex BTW)",  f"€ {omzet:,.2f}")
c2.metric("Kosten (ex BTW)", f"€ {kosten:,.2f}")
c3.metric("Winst",           f"€ {winst:,.2f}")
c4.metric("BTW saldo",       f"€ {btw_sal:,.2f}",
          help="Positief = te betalen aan Belastingdienst")

st.divider()


def _totals_row(edited_df: pd.DataFrame, money_cols: list[str],
                all_cols: list[str], col_cfg: dict, label_col: str = "naam") -> None:
    """Render a totals row using the same column config so columns stay aligned."""
    if edited_df.empty:
        return
    row: dict = {}
    for c in all_cols:
        if c in money_cols:
            row[c] = round(float(edited_df[c].fillna(0).sum()), 2)
        elif c == label_col:
            row[c] = "— Totaal —"
        else:
            row[c] = None
    totals_df = pd.DataFrame([row])
    st.dataframe(totals_df, column_config=col_cfg, use_container_width=True, hide_index=True)


# ── Inkomsten ─────────────────────────────────────────────────────────────────

st.subheader("📥 Inkomsten")
st.caption("Ex BTW is het primaire invoerveld; BTW en Totaal worden herberekend bij opslaan.")

inc_cols = ["factuur", "naam", "datum", "project", "btw_pct", "ex_btw", "btw", "total", "betaald"]
if kw_num is None:
    inc_cols = ["kwartaal"] + inc_cols

inc_display = inc_df[inc_cols].copy() if not inc_df.empty else pd.DataFrame(columns=inc_cols)

inc_col_cfg = {
    "kwartaal": st.column_config.SelectboxColumn("Q",       options=[1, 2, 3, 4], width="small"),
    "factuur":  st.column_config.TextColumn(     "Factuur", width="small"),
    "naam":     st.column_config.TextColumn(     "Klant",   width="medium"),
    "datum":    st.column_config.DateColumn(     "Datum",   format="DD-MM-YYYY",  width="small"),
    "project":  st.column_config.TextColumn(     "Project", width="medium"),
    "btw_pct":  st.column_config.SelectboxColumn("BTW %",   options=[0, 9, 21],   width="small"),
    "ex_btw":   st.column_config.NumberColumn(   "Ex BTW",  format="€ %.2f",      width="small"),
    "btw":      st.column_config.NumberColumn(   "BTW",     format="€ %.2f",      width="small"),
    "total":    st.column_config.NumberColumn(   "Totaal",  format="€ %.2f",      width="small"),
    "betaald":  st.column_config.CheckboxColumn( "Betaald",                        width="small"),
}

inc_edited = st.data_editor(
    inc_display, column_config=inc_col_cfg,
    num_rows="dynamic", use_container_width=True, hide_index=True,
    key=f"inc_{jaar}_{kw_label}",
)
_totals_row(inc_edited, ["ex_btw", "btw", "total"], inc_cols, inc_col_cfg, label_col="naam")

if st.button("💾 Inkomsten opslaan", type="primary", key="save_inc"):
    save_income(inc_edited, jaar, kw_num)
    st.success("Inkomsten opgeslagen.")
    st.rerun()

st.divider()

# ── Uitgaven ──────────────────────────────────────────────────────────────────

st.subheader("📤 Uitgaven")
st.caption("Totaal (incl. BTW) is het primaire invoerveld; Ex BTW en BTW worden herberekend bij opslaan.")

exp_cols = ["factuur", "naam", "datum", "categorie", "btw_pct", "total", "ex_btw", "btw", "afgerekend"]
if kw_num is None:
    exp_cols = ["kwartaal"] + exp_cols

exp_display_full = exp_df[exp_cols].copy() if not exp_df.empty else pd.DataFrame(columns=exp_cols)

filter_naam = st.text_input("Filter op naam", key="exp_naam_filter", placeholder="Type om te filteren…")
if filter_naam:
    exp_display = exp_display_full[exp_display_full["naam"].str.contains(filter_naam, case=False, na=False)].copy()
else:
    exp_display = exp_display_full

visible_ids = set(exp_df["id"].iloc[exp_display.index].dropna().astype(int)) if "id" in exp_df.columns and not exp_display.empty else set()

exp_col_cfg = {
    "kwartaal":   st.column_config.SelectboxColumn("Q",          options=[1, 2, 3, 4],  width="small"),
    "factuur":    st.column_config.TextColumn(     "Factuur",    width="small"),
    "naam":       st.column_config.TextColumn(     "Naam",       width="medium"),
    "datum":      st.column_config.DateColumn(     "Datum",      format="DD-MM-YYYY",   width="small"),
    "categorie":  st.column_config.SelectboxColumn("Categorie",  options=categories,    width="medium"),
    "btw_pct":    st.column_config.SelectboxColumn("BTW %",      options=[0, 9, 21],    width="small"),
    "total":      st.column_config.NumberColumn(   "Totaal",     format="€ %.2f",       width="small"),
    "ex_btw":     st.column_config.NumberColumn(   "Ex BTW",     format="€ %.2f",       width="small"),
    "btw":        st.column_config.NumberColumn(   "BTW",        format="€ %.2f",       width="small"),
    "afgerekend": st.column_config.CheckboxColumn( "Afgerekend",                        width="small"),
}

exp_edited = st.data_editor(
    exp_display, column_config=exp_col_cfg,
    num_rows="dynamic", use_container_width=True, hide_index=True,
    key=f"exp_{jaar}_{kw_label}_{filter_naam}",
)
_totals_row(exp_edited, ["total", "ex_btw", "btw"], exp_cols, exp_col_cfg, label_col="naam")

if st.button("💾 Uitgaven opslaan", type="primary", key="save_exp"):
    if filter_naam and visible_ids:
        # Merge edited visible rows with untouched hidden rows
        fresh = get_expenses(jaar, kw_num)
        unchanged = fresh[~fresh["id"].isin(visible_ids)]
        final = pd.concat([unchanged[exp_cols], exp_edited], ignore_index=True)
    else:
        final = exp_edited
    save_expenses(final, jaar, kw_num)
    st.success("Uitgaven opgeslagen.")
    st.rerun()
