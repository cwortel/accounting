import streamlit as st
import pandas as pd
from db import (
    init_db, get_yearly_summary, get_btw_by_quarter,
    get_expense_by_category_quarter,
)

st.set_page_config(
    page_title="Green Light Boekhouding",
    page_icon="💚",
    layout="wide",
)

init_db()

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024], key="jaar")

st.title("💚 Green Light Boekhouding")
st.caption(f"Jaaroverzicht {jaar}")

# ── Top metrics ───────────────────────────────────────────────────────────────

summary = get_yearly_summary(jaar)
totals = summary[["omzet", "kosten", "winst", "btw_in", "btw_uit", "btw_saldo"]].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Omzet (ex BTW)",  f"€ {totals['omzet']:,.2f}")
c2.metric("Kosten (ex BTW)", f"€ {totals['kosten']:,.2f}")
c3.metric("Winst (ex BTW)",  f"€ {totals['winst']:,.2f}")
c4.metric("BTW saldo",       f"€ {totals['btw_saldo']:,.2f}",
          help="Positief = te betalen aan Belastingdienst")

st.divider()

# ── Combined per kwartaal table ───────────────────────────────────────────────

st.subheader("Per kwartaal")

inc_btw, exp_btw = get_btw_by_quarter(jaar)
combined_rows = []
for q in range(1, 5):
    s = summary[summary["kwartaal"] == q].iloc[0] if not summary[summary["kwartaal"] == q].empty else {}
    inc_q = inc_btw[inc_btw["kwartaal"] == q] if not inc_btw.empty else pd.DataFrame()
    exp_q = exp_btw[exp_btw["kwartaal"] == q] if not exp_btw.empty else pd.DataFrame()
    grond_21 = inc_q[inc_q["btw_pct"] == 21]["grondslag"].sum() if not inc_q.empty else 0
    btw_21   = inc_q[inc_q["btw_pct"] == 21]["btw"].sum()       if not inc_q.empty else 0
    grond_9  = inc_q[inc_q["btw_pct"] == 9]["grondslag"].sum()  if not inc_q.empty else 0
    btw_9    = inc_q[inc_q["btw_pct"] == 9]["btw"].sum()        if not inc_q.empty else 0
    aftrek   = exp_q["aftrekbare_btw"].sum()                     if not exp_q.empty else 0
    saldo    = btw_21 + btw_9 - aftrek
    combined_rows.append({
        "Kwartaal":              f"Q{q}",
        "Omzet":                 float(s.get("omzet", 0)),
        "Grondslag 21%":         grond_21,
        "BTW 21%":               btw_21,
        "Grondslag 9%":          grond_9,
        "BTW 9%":                btw_9,
        "Kosten":                float(s.get("kosten", 0)),
        "Aftrekbare BTW":        aftrek,
        "Winst":                 float(s.get("winst", 0)),
        "Te betalen / ontvangen": saldo,
    })

combined_df = pd.DataFrame(combined_rows)
comb_money = ["Omzet", "Grondslag 21%", "BTW 21%", "Grondslag 9%", "BTW 9%",
              "Kosten", "Aftrekbare BTW", "Winst", "Te betalen / ontvangen"]
comb_totals = {c: combined_df[c].sum() for c in comb_money}
comb_totals["Kwartaal"] = "Totaal"
combined_df = pd.concat([combined_df, pd.DataFrame([comb_totals])], ignore_index=True)

st.dataframe(
    combined_df[["Kwartaal"] + comb_money],
    hide_index=True,
    use_container_width=True,
    column_config={col: st.column_config.NumberColumn(format="€ %.2f") for col in comb_money},
)

st.subheader("Per kwartaal — aangifte detail")
for q in range(1, 5):
    row = combined_df[combined_df["Kwartaal"] == f"Q{q}"]
    if row.empty:
        continue
    row = row.iloc[0]
    saldo = row["Te betalen / ontvangen"]
    if saldo == 0 and row["BTW 21%"] == 0:
        label = f"Q{q} — geen omzet"
    elif saldo > 0:
        label = f"Q{q} — € {saldo:,.2f} te betalen"
    else:
        label = f"Q{q} — € {abs(saldo):,.2f} terug te vragen"
    with st.expander(label):
        ca, cb = st.columns(2)
        with ca:
            st.markdown("**Omzet BTW**")
            st.write(f"1a. Hoog tarief 21% — grondslag: € {row['Grondslag 21%']:,.2f}")
            st.write(f"1a. Hoog tarief 21% — BTW: **€ {row['BTW 21%']:,.2f}**")
            if row["Grondslag 9%"] > 0:
                st.write(f"1b. Laag tarief 9% — grondslag: € {row['Grondslag 9%']:,.2f}")
                st.write(f"1b. Laag tarief 9% — BTW: **€ {row['BTW 9%']:,.2f}**")
        with cb:
            st.markdown("**Voorbelasting**")
            st.write(f"5b. Aftrekbare BTW (inkoop/kosten): **€ {row['Aftrekbare BTW']:,.2f}**")
            st.divider()
            if saldo > 0:
                st.error(f"Te betalen: € {saldo:,.2f}")
            elif saldo < 0:
                st.success(f"Terug te vragen: € {abs(saldo):,.2f}")
            else:
                st.info("Saldo: € 0,00")

st.divider()

# ── Kosten per categorie (pivot tabel) ───────────────────────────────────────

st.subheader("Kosten per categorie (ex BTW)")

cat_q = get_expense_by_category_quarter(jaar)
if not cat_q.empty:
    money_cat = ["Q1", "Q2", "Q3", "Q4", "Totaal"]
    # Hide categories with no spending so totals row stays visible
    cat_q = cat_q[cat_q["Totaal"] > 0].copy()
    # Validate: category sums must match actual costs per quarter
    mismatches = []
    for q_label, q_num in [("Q1", 1), ("Q2", 2), ("Q3", 3), ("Q4", 4)]:
        cat_sum = cat_q[q_label].sum()
        actual_row = combined_df[combined_df["Kwartaal"] == f"Q{q_num}"]
        actual_val = float(actual_row["Kosten"].iloc[0]) if not actual_row.empty else 0.0
        if abs(cat_sum - actual_val) > 0.01:
            diff = cat_sum - actual_val
            mismatches.append(
                f"**Q{q_num}**: categorieën € {cat_sum:,.2f} ≠ kosten € {actual_val:,.2f} "
                f"(verschil € {diff:+,.2f})"
            )
    if mismatches:
        st.warning("⚠️ Som van categorieën klopt niet met totale kosten:\n\n" + "\n\n".join(mismatches))

    cat_totals = {c: cat_q[c].sum() for c in money_cat}
    cat_totals["Categorie"] = "Totaal"
    cat_q = pd.concat([cat_q, pd.DataFrame([cat_totals])], ignore_index=True)
    st.dataframe(
        cat_q,
        hide_index=True,
        use_container_width=True,
        column_config={col: st.column_config.NumberColumn(format="€ %.2f") for col in money_cat},
    )
