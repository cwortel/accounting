import streamlit as st
import pandas as pd
from db import init_db, get_btw_by_quarter

st.set_page_config(page_title="BTW Overzicht", page_icon="🧾", layout="wide")
init_db()

st.title("🧾 BTW Overzicht")
st.caption("Basis voor je kwartaalaangifte bij de Belastingdienst.")

if "jaar" not in st.session_state:
    st.session_state["jaar"] = 2026

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024], key="jaar")

inc_btw, exp_btw = get_btw_by_quarter(jaar)

# Build per-quarter summary table
rows = []
for q in range(1, 5):
    inc_q = inc_btw[inc_btw["kwartaal"] == q] if not inc_btw.empty else pd.DataFrame()
    exp_q = exp_btw[exp_btw["kwartaal"] == q] if not exp_btw.empty else pd.DataFrame()

    grond_21 = inc_q[inc_q["btw_pct"] == 21]["grondslag"].sum() if not inc_q.empty else 0
    btw_21   = inc_q[inc_q["btw_pct"] == 21]["btw"].sum()       if not inc_q.empty else 0
    grond_9  = inc_q[inc_q["btw_pct"] == 9]["grondslag"].sum()  if not inc_q.empty else 0
    btw_9    = inc_q[inc_q["btw_pct"] == 9]["btw"].sum()        if not inc_q.empty else 0
    aftrek   = exp_q["aftrekbare_btw"].sum()                     if not exp_q.empty else 0
    saldo    = btw_21 + btw_9 - aftrek

    rows.append({
        "Kwartaal":              f"Q{q}",
        "Grondslag 21%":         grond_21,
        "BTW 21%":               btw_21,
        "Grondslag 9%":          grond_9,
        "BTW 9%":                btw_9,
        "Aftrekbare BTW":        aftrek,
        "Te betalen / terug":    saldo,
    })

result = pd.DataFrame(rows)

# Totals row
totals = result.drop(columns=["Kwartaal"]).sum()
totals["Kwartaal"] = "Totaal"
result = pd.concat([result, pd.DataFrame([totals])], ignore_index=True)

money_cols = ["Grondslag 21%", "BTW 21%", "Grondslag 9%", "BTW 9%", "Aftrekbare BTW", "Te betalen / terug"]
st.dataframe(
    result[["Kwartaal"] + money_cols],
    hide_index=True,
    use_container_width=True,
    column_config={col: st.column_config.NumberColumn(format="€ %.2f") for col in money_cols},
)

st.divider()
st.subheader("Per kwartaal — aangifte detail")

for q in range(1, 5):
    row = result[result["Kwartaal"] == f"Q{q}"]
    if row.empty:
        continue
    row = row.iloc[0]
    saldo = row["Te betalen / terug"]
    if saldo == 0 and row["BTW 21%"] == 0:
        label = f"Q{q} — geen omzet"
    elif saldo > 0:
        label = f"Q{q} — € {saldo:,.2f} te betalen"
    else:
        label = f"Q{q} — € {abs(saldo):,.2f} terug te vragen"

    with st.expander(label):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Omzet BTW**")
            st.write(f"1a. Hoog tarief 21% — grondslag: € {row['Grondslag 21%']:,.2f}")
            st.write(f"1a. Hoog tarief 21% — BTW: **€ {row['BTW 21%']:,.2f}**")
            if row["Grondslag 9%"] > 0:
                st.write(f"1b. Laag tarief 9% — grondslag: € {row['Grondslag 9%']:,.2f}")
                st.write(f"1b. Laag tarief 9% — BTW: **€ {row['BTW 9%']:,.2f}**")
        with c2:
            st.markdown("**Voorbelasting**")
            st.write(f"5b. Aftrekbare BTW (inkoop/kosten): **€ {row['Aftrekbare BTW']:,.2f}**")
            st.divider()
            if saldo > 0:
                st.error(f"Te betalen: € {saldo:,.2f}")
            elif saldo < 0:
                st.success(f"Terug te vragen: € {abs(saldo):,.2f}")
            else:
                st.info("Saldo: € 0,00")
