import streamlit as st
import pandas as pd
from db import init_db, get_income, save_income

st.set_page_config(page_title="Inkomsten", page_icon="📥", layout="wide")
init_db()

st.title("📥 Inkomsten")

if "jaar" not in st.session_state:
    st.session_state["jaar"] = 2026

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024], key="jaar")
kw_label = st.sidebar.selectbox("Kwartaal", ["Alle", "Q1", "Q2", "Q3", "Q4"])
kw_num = None if kw_label == "Alle" else int(kw_label[1])

df = get_income(jaar, kw_num)

show_cols = ["factuur", "naam", "datum", "project", "btw_pct", "ex_btw", "btw", "total", "betaald"]
if kw_num is None:
    show_cols = ["kwartaal"] + show_cols

display_df = df[show_cols].copy() if not df.empty else pd.DataFrame(columns=show_cols)

col_config = {
    "kwartaal": st.column_config.SelectboxColumn("Q",        options=[1, 2, 3, 4],  width="small"),
    "factuur":  st.column_config.TextColumn(     "Factuur",  width="small"),
    "naam":     st.column_config.TextColumn(     "Klant",    width="medium"),
    "datum":    st.column_config.DateColumn(     "Datum",    format="DD-MM-YYYY",   width="small"),
    "project":  st.column_config.TextColumn(     "Project",  width="medium"),
    "btw_pct":  st.column_config.SelectboxColumn("BTW %",    options=[0, 9, 21],    width="small"),
    "ex_btw":   st.column_config.NumberColumn(   "Ex BTW",   format="€ %.2f",       width="small"),
    "btw":      st.column_config.NumberColumn(   "BTW",      format="€ %.2f",       width="small"),
    "total":    st.column_config.NumberColumn(   "Totaal",   format="€ %.2f",       width="small"),
    "betaald":  st.column_config.CheckboxColumn( "Betaald",                          width="small"),
}

st.caption("Voeg rijen toe onderaan. BTW en Totaal worden herberekend (Ex BTW × BTW %) bij opslaan.")

edited = st.data_editor(
    display_df,
    column_config=col_config,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key=f"inc_{jaar}_{kw_label}",
)

if not edited.empty:
    ex = edited["ex_btw"].fillna(0).sum()
    btw = edited["btw"].fillna(0).sum()
    tot = edited["total"].fillna(0).sum()
    st.info(
        f"Totaal ex BTW: **€ {ex:,.2f}** &nbsp;|&nbsp; "
        f"BTW: **€ {btw:,.2f}** &nbsp;|&nbsp; "
        f"Incl. BTW: **€ {tot:,.2f}**"
    )

if st.button("💾 Opslaan", type="primary"):
    save_income(edited, jaar, kw_num)
    st.success("Opgeslagen!")
    st.rerun()
