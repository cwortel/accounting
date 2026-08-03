import streamlit as st
import altair as alt
from db import init_db, get_yearly_summary, get_expense_by_category

st.set_page_config(
    page_title="Green Light Boekhouding",
    page_icon="💚",
    layout="wide",
)

init_db()

if "jaar" not in st.session_state:
    st.session_state["jaar"] = 2026

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024], key="jaar")

st.title("💚 Green Light Boekhouding")
st.caption(f"Jaaroverzicht {jaar}")

summary = get_yearly_summary(jaar)
totals = summary[["omzet", "kosten", "winst", "btw_in", "btw_uit", "btw_saldo"]].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Omzet (ex BTW)", f"€ {totals['omzet']:,.2f}")
c2.metric("Kosten (ex BTW)", f"€ {totals['kosten']:,.2f}")
c3.metric("Winst (ex BTW)", f"€ {totals['winst']:,.2f}")
c4.metric(
    "BTW saldo",
    f"€ {totals['btw_saldo']:,.2f}",
    help="Positief = te betalen aan Belastingdienst",
)

st.divider()

st.subheader("Per kwartaal")
disp = summary.copy()
disp["Kwartaal"] = disp["kwartaal"].apply(lambda q: f"Q{int(q)}")
disp = disp.rename(columns={
    "omzet": "Omzet",
    "kosten": "Kosten",
    "winst": "Winst",
    "btw_in": "BTW omzet",
    "btw_uit": "BTW kosten",
    "btw_saldo": "BTW saldo",
})
money_cols = ["Omzet", "Kosten", "Winst", "BTW omzet", "BTW kosten", "BTW saldo"]
st.dataframe(
    disp[["Kwartaal"] + money_cols],
    hide_index=True,
    use_container_width=True,
    column_config={col: st.column_config.NumberColumn(format="€ %.2f") for col in money_cols},
)

st.divider()

cat_df = get_expense_by_category(jaar)
if not cat_df.empty and cat_df["totaal"].sum() > 0:
    st.subheader("Kosten per categorie (ex BTW)")
    cat_df = cat_df.sort_values("totaal", ascending=False)
    bars = alt.Chart(cat_df).mark_bar().encode(
        x=alt.X("totaal:Q", title="Bedrag (ex BTW)"),
        y=alt.Y("categorie:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("categorie:N", title="Categorie"),
                 alt.Tooltip("totaal:Q", title="Bedrag", format=",.2f")],
    )
    labels = bars.mark_text(align="left", dx=4).encode(
        text=alt.Text("totaal:Q", format=",.0f")
    )
    st.altair_chart(bars + labels, use_container_width=True)
