import calendar
import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
from dateutil.relativedelta import relativedelta
from db import init_db, get_connection, get_rekeningen, get_schulden, get_btw_betalingen, get_setting, set_setting

st.set_page_config(page_title="Prognose", page_icon="📈", layout="wide")
init_db()

ZAKELIJK_IBANS = ["NL84RABO0188971130", "NL49RABO3161681290"]  # betaal + spaar
ZAKELIJK_BETAAL = ZAKELIJK_IBANS[0]
MAAND = ["", "Jan", "Feb", "Mrt", "Apr", "Mei", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dec"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Instellingen")

st.sidebar.subheader("🎯 Doelstelling")
buffer_min   = st.sidebar.number_input("Buffer min (€)",  value=55_000, step=1_000)
buffer_max   = st.sidebar.number_input("Buffer max (€)",  value=70_000, step=1_000)
target_year  = st.sidebar.selectbox("Doeljaar",  [2027, 2028, 2026])
target_month = st.sidebar.selectbox(
    "Doelmaand", list(range(1, 13)), format_func=lambda m: MAAND[m], index=5,
)

st.sidebar.subheader("⚡ Aannames")
_saved_beginsaldo = int(float(get_setting("prognose_beginsaldo", "0")))
beginsaldo    = st.sidebar.number_input(
    "Beginsaldo 1 jan (betaal+spaar) (€)", value=_saved_beginsaldo, step=1_000,
    help="Totaal zakelijk saldo op 1 januari van het basisjaar",
)
set_setting("prognose_beginsaldo", str(int(beginsaldo)))
runrate_months = st.sidebar.selectbox("Run-rate venster", [3, 6], format_func=lambda x: f"{x} maanden")
omzet_adj      = st.sidebar.slider("Omzet bijstelling (%)", -50, 50, 0)
prive_monthly  = st.sidebar.number_input(
    "Privé onttrekking p/m (€)", value=8_000, step=500,
    help="Gemiddeld maandelijks over te maken naar privérekening",
)
btw_per_q    = st.sidebar.number_input("BTW per kwartaal (€)",       value=11_000, step=500)
ib_per_jaar  = st.sidebar.number_input("Inkomstenbelasting p/j (€)", value=65_000, step=1_000)

# ── Load current saldo (betaal + spaar combined) ──────────────────────────────
rek_df = get_rekeningen()
current_saldo = 0.0
if not rek_df.empty:
    current_saldo = float(
        rek_df[rek_df["iban"].isin(ZAKELIJK_IBANS)]["saldo"].fillna(0).sum()
    )

today       = date.today()
today_month = pd.Timestamp(today.replace(day=1))
target_date = date(target_year, target_month, calendar.monthrange(target_year, target_month)[1])

# ── Load historical P&L from invoice tables ───────────────────────────────────
with get_connection() as conn:
    inc_raw = pd.read_sql_query(
        "SELECT strftime('%Y-%m', datum) as month, SUM(total) as omzet "
        "FROM income WHERE datum IS NOT NULL AND datum!='' AND total>0 "
        "GROUP BY month ORDER BY month",
        conn,
    )
    exp_raw = pd.read_sql_query(
        "SELECT strftime('%Y-%m', datum) as month, SUM(total) as kosten "
        "FROM expenses WHERE datum IS NOT NULL AND datum!='' "
        "  AND total>0 AND categorie!='Taxes' "
        "GROUP BY month ORDER BY month",
        conn,
    )
    prive_raw = pd.read_sql_query(
        "SELECT strftime('%Y-%m', datum) as month, SUM(ABS(bedrag)) as prive_out "
        "FROM bank_transactions WHERE rekening=? AND prive=1 AND bedrag<0 "
        "GROUP BY month ORDER BY month",
        conn, params=[ZAKELIJK_BETAAL],
    )
    btw_paid_raw = pd.read_sql_query(
        "SELECT strftime('%Y-%m', datum) as month, SUM(ABS(bedrag)) as btw_paid "
        "FROM bank_transactions WHERE btw_betaling=1 "
        "GROUP BY month ORDER BY month",
        conn,
    )
    rec_raw = pd.read_sql_query(
        "SELECT strftime('%Y-%m', datum) as month, SUM(ABS(bedrag)) as totaal "
        "FROM bank_transactions "
        "WHERE rekening IN (SELECT iban FROM rekeningen WHERE type='prive') "
        "  AND is_recurring=1 AND bedrag<0 "
        "GROUP BY month ORDER BY month",
        conn,
    )
    spend_raw = pd.read_sql_query(
        "SELECT strftime('%Y-%m', datum) as month, SUM(ABS(bedrag)) as totaal "
        "FROM bank_transactions "
        "WHERE rekening IN (SELECT iban FROM rekeningen WHERE type='prive') "
        "  AND bedrag<0 "
        "GROUP BY month ORDER BY month",
        conn,
    )

def _to_series(df, col):
    if df.empty:
        return pd.Series(dtype=float)
    df = df.copy()
    df.index = pd.to_datetime(df["month"] + "-01")
    return df[col].astype(float)

s_omzet  = _to_series(inc_raw,      "omzet")
s_kosten = _to_series(exp_raw,      "kosten")
s_prive  = _to_series(prive_raw,    "prive_out")
s_btw    = _to_series(btw_paid_raw, "btw_paid")

# ── Build monthly cashflow (historical, forward from beginsaldo) ──────────────
# Restrict to the year(s) where we have both omzet and prive data (2026 onwards)
base_year = today.year
base_start = pd.Timestamp(f"{base_year}-01-01")

hist_months = sorted(
    m for m in (set(s_omzet.index) | set(s_kosten.index))
    if base_start <= m < today_month
    and float(s_omzet.get(m, 0)) + float(s_kosten.get(m, 0)) > 0
)

cf_df = pd.DataFrame([
    {
        "month_dt": m,
        "omzet":  float(s_omzet.get(m,  0)),
        "kosten": float(s_kosten.get(m, 0)),
        "prive":  float(s_prive.get(m,  0)),
        "btw":    float(s_btw.get(m,    0)),
    }
    for m in hist_months
]) if hist_months else pd.DataFrame(columns=["month_dt","omzet","kosten","prive","btw"])

cf_df["net"] = cf_df["omzet"] - cf_df["kosten"] - cf_df["prive"] - cf_df["btw"]

# Build actuals forward from beginsaldo (if provided), else fall back to today-only
actuals_df = pd.DataFrame()
last_saldo  = current_saldo
last_dt     = today_month

if beginsaldo > 0 and not cf_df.empty:
    cf_df["cumsum"] = cf_df["net"].cumsum()
    cf_df["saldo"]  = float(beginsaldo) + cf_df["cumsum"]
    # Append today's known saldo as final point so the solid line ends at reality
    today_row = pd.DataFrame([{"month_dt": today_month, "saldo": current_saldo}])
    actuals_df = pd.concat([cf_df[["month_dt", "saldo"]], today_row], ignore_index=True)
    last_dt    = today_month
elif not cf_df.empty:
    # No beginsaldo: show today only as the starting point
    actuals_df = pd.DataFrame([{"month_dt": today_month, "saldo": current_saldo}])
    last_dt = today_month

# ── Run-rate from recent complete months ──────────────────────────────────────
avg_omzet = avg_kosten = avg_prive_hist = 0.0
if not cf_df.empty:
    cutoff = today_month - pd.DateOffset(months=runrate_months)
    recent = cf_df[cf_df["month_dt"] >= cutoff]
    if not recent.empty:
        avg_omzet      = float(recent["omzet"].mean())
        avg_kosten     = float(recent["kosten"].mean())
        avg_prive_hist = float(recent["prive"].mean())

adj_omzet   = avg_omzet * (1 + omzet_adj / 100)
monthly_net = adj_omzet - avg_kosten - float(prive_monthly)
ib_monthly  = ib_per_jaar / 12

avg_recurring = 0.0
if not rec_raw.empty:
    rec_raw["month_dt"] = pd.to_datetime(rec_raw["month"] + "-01")
    cutoff_rec = today_month - pd.DateOffset(months=runrate_months)
    rr = rec_raw[(rec_raw["month_dt"] >= cutoff_rec) & (rec_raw["month_dt"] < today_month)]
    avg_recurring = float(rr["totaal"].mean()) if not rr.empty else 0.0

avg_spending = 0.0
if not spend_raw.empty:
    spend_raw["month_dt"] = pd.to_datetime(spend_raw["month"] + "-01")
    cutoff_sp = today_month - pd.DateOffset(months=runrate_months)
    sp = spend_raw[(spend_raw["month_dt"] >= cutoff_sp) & (spend_raw["month_dt"] < today_month)]
    avg_spending = float(sp["totaal"].mean()) if not sp.empty else 0.0

# ── BTW schedule: future unpaid obligations ───────────────────────────────────
def _btw_due(year, quarter):
    month = quarter * 3 + 1
    if month > 12:
        month, year = month - 12, year + 1
    return date(year, month, calendar.monthrange(year, month)[1])

btw_schedule = []
for yr in [today.year, today.year + 1]:
    paid = get_btw_betalingen(yr)
    for q in range(1, 5):
        due = _btw_due(yr, q)
        if today <= due <= target_date and q not in paid:
            btw_schedule.append({"label": f"BTW Q{q} {yr}", "due": due, "bedrag": btw_per_q})

# ── Month-by-month projection starting from today's known saldo ──────────────
proj_rows = [{"month_dt": today_month, "saldo": current_saldo}]
proj_saldo = current_saldo
cursor = (today_month + pd.DateOffset(months=1)).date().replace(day=1)
while cursor <= target_date:
    month_end = date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
    delta = monthly_net - ib_monthly
    for btw in btw_schedule:
        if cursor <= btw["due"] <= month_end:
            delta -= btw["bedrag"]
    proj_saldo += delta
    proj_rows.append({"month_dt": pd.Timestamp(cursor), "saldo": proj_saldo})
    cursor = (cursor + relativedelta(months=1)).replace(day=1)

proj_df = pd.DataFrame(proj_rows)

# ── KPI metrics ───────────────────────────────────────────────────────────────
projected_end = float(proj_df["saldo"].iloc[-1]) if not proj_df.empty else current_saldo
gap           = projected_end - buffer_min
runway        = current_saldo / (avg_kosten + float(prive_monthly)) if (avg_kosten + float(prive_monthly)) > 0 else float("inf")

st.title("📈 Prognose")
st.caption(
    f"Doelstelling: € {buffer_min:,.0f}–{buffer_max:,.0f} zakelijk (betaal+spaar) "
    f"per {MAAND[target_month]} {target_year}"
)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Totaal zakelijk saldo", f"€ {current_saldo:,.0f}",
          help="Betaalrekening + spaarrekening")
c2.metric(
    f"Prognose {MAAND[target_month]} {target_year}",
    f"€ {projected_end:,.0f}",
    delta=f"€ {gap:+,.0f} t.o.v. buffer min",
    delta_color="normal" if gap >= 0 else "inverse",
)
c3.metric(
    "Run-rate netto p/m", f"€ {monthly_net:+,.0f}",
    help=f"Omzet € {avg_omzet:,.0f} − kosten € {avg_kosten:,.0f} − privé € {prive_monthly:,.0f}",
)
c4.metric(
    "Gem. totaal privé p/m", f"€ {avg_spending:,.0f}",
    help=f"Alle privé uitgaven gemiddeld (laatste {runrate_months} mnd) — referentie voor privé onttrekking",
)
c5.metric(
    "Gem. vaste lasten p/m", f"€ {avg_recurring:,.0f}",
    delta=f"€ {avg_spending - avg_recurring:,.0f} variabel" if avg_spending > 0 else None,
    delta_color="off",
    help="Terugkerende privé lasten (subset van totaal privé)",
)
c6.metric(
    "Runway", f"{runway:.1f} mnd" if runway != float("inf") else "∞",
    help="Huidig saldo ÷ (gem. kosten + privé onttrekking p/m)",
)

st.divider()

# ── Chart ─────────────────────────────────────────────────────────────────────
if not proj_df.empty:
    # Single tidy DataFrame avoids Altair 6 multi-source layer scale conflicts
    frames = []
    if not actuals_df.empty:
        a = actuals_df[["month_dt", "saldo"]].copy()
        a["lijn"] = "Actueel"
        frames.append(a)
    p = proj_df[["month_dt", "saldo"]].copy()
    p["lijn"] = "Prognose"
    frames.append(p)
    plot_df = pd.concat(frames, ignore_index=True)

    lines = (alt.Chart(plot_df)
             .mark_line(strokeWidth=2.5, point={"filled": True, "size": 50}, color="#2563EB")
             .encode(
                 x=alt.X("month_dt:T", title=None,
                          axis=alt.Axis(format="%b '%y", labelAngle=-30, tickCount="month")),
                 y=alt.Y("saldo:Q", title="Totaal zakelijk saldo (€)",
                          axis=alt.Axis(format=",.0f")),
                 strokeDash=alt.StrokeDash("lijn:N",
                     scale=alt.Scale(domain=["Actueel", "Prognose"], range=[[1, 0], [6, 3]]),
                     legend=None),
                 tooltip=[alt.Tooltip("month_dt:T", title="Maand", format="%b %Y"),
                          alt.Tooltip("saldo:Q", title="Saldo (€)", format=",.0f")],
             ))

    # Two horizontal rules for buffer boundaries; mark_rule needs no x/x2
    buf_df = pd.DataFrame({"v": [float(buffer_min), float(buffer_max)]})
    band = (alt.Chart(buf_df)
            .mark_rule(strokeDash=[4, 4], color="#F59E0B", opacity=0.7)
            .encode(y=alt.Y("v:Q", axis=None)))

    st.altair_chart((lines + band).properties(height=380), use_container_width=True)

    if not actuals_df.empty and beginsaldo > 0:
        st.caption("**—** Actueel (op basis van beginsaldo + factuurdata)  **╌** Prognose  🟡 Buffer zone")
    else:
        st.caption("**╌** Prognose  🟡 Buffer zone — voer beginsaldo in voor historische lijn")
else:
    st.info("Geen prognosedata beschikbaar.")

st.divider()

# ── Obligations table ─────────────────────────────────────────────────────────
st.subheader("📋 Geplande verplichtingen")
rows = []
for btw in btw_schedule:
    rows.append({"Type": "BTW aangifte", "Omschrijving": btw["label"],
                  "Vervaldatum": btw["due"], "Bedrag (€)": -float(btw["bedrag"])})

months_to_target = max(0, (target_date - today).days // 30)
rows.append({"Type": "IB reservering",
              "Omschrijving": f"Inkomstenbelasting — {months_to_target} mnd × € {ib_monthly:,.0f}",
              "Vervaldatum": target_date, "Bedrag (€)": -(ib_monthly * months_to_target)})

schulden_df = get_schulden(only_actief=True)
if not schulden_df.empty:
    for _, s in schulden_df.iterrows():
        if float(s.get("huidig_restant") or 0) <= 0:
            continue
        freq      = str(s.get("frequentie") or "maandelijks")
        remaining = max(0, int(s.get("aantal_termijnen") or 0) - int(s.get("betaald_termijnen") or 0))
        try:
            next_dt = pd.to_datetime(s["betaaldatum"]).date() if s.get("betaaldatum") else None
        except Exception:
            next_dt = None
        rows.append({"Type": "Lening (privé)",
                      "Omschrijving": f"{s['naam']} — {remaining}× {freq} resterend",
                      "Vervaldatum": next_dt, "Bedrag (€)": -float(s.get("termijn_bedrag") or 0)})

if rows:
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 column_config={
                     "Vervaldatum": st.column_config.DateColumn("Vervaldatum", format="DD-MM-YYYY"),
                     "Bedrag (€)":  st.column_config.NumberColumn("Bedrag (€)", format="€ %.2f"),
                 })
st.caption("ℹ️ Leningen zijn ter informatie — betaald via privérekening, impliciet in privé onttrekking p/m.")

# ── Run-rate detail ───────────────────────────────────────────────────────────
with st.expander("📊 Run-rate aannames", expanded=False):
    st.caption(f"Gebaseerd op laatste {runrate_months} maanden factuurdata. "
               f"Historisch gemiddelde privé onttrekking: € {avg_prive_hist:,.0f}/mnd.")
    rr1, rr2, rr3, rr4, rr5 = st.columns(5)
    rr1.metric("Gem. omzet p/m",        f"€ {avg_omzet:,.0f}")
    rr2.metric(f"Na bijstelling ({omzet_adj:+d}%)", f"€ {adj_omzet:,.0f}")
    rr3.metric("Gem. kosten p/m",       f"€ {avg_kosten:,.0f}")
    rr4.metric("Privé onttrekking p/m", f"€ {prive_monthly:,.0f}")
    rr5.metric("IB reservering p/m",    f"€ {ib_monthly:,.0f}")
    st.info(f"Maandelijkse zakelijke netto-accumulatie (na kosten, privé en IB): "
            f"**€ {monthly_net - ib_monthly:+,.0f}**")
