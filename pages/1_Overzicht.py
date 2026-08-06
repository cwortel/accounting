import streamlit as st
import pandas as pd
from db import (
    init_db, get_income, save_income, get_expenses, save_expenses, get_categories,
    get_matched_income_ids, get_matched_expense_ids, get_bank_info_for_expenses,
    unlink_bank_transaction,
)

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
all_exp_df = get_expenses(jaar, None)
matched_inc_ids = get_matched_income_ids(jaar)
matched_exp_ids = get_matched_expense_ids(jaar)
bank_info_by_expense_id = {}
if "id" in all_exp_df.columns and not all_exp_df.empty:
    expense_ids = all_exp_df["id"].dropna().astype(int).tolist()
    bank_info_by_expense_id = get_bank_info_for_expenses(expense_ids)

# ── Summary metrics ───────────────────────────────────────────────────────────

omzet  = float(inc_df["ex_btw"].sum()) if not inc_df.empty else 0.0
kosten = float(exp_df["ex_btw"].sum()) if not exp_df.empty else 0.0
btw_in  = float(inc_df["btw"].sum())   if not inc_df.empty else 0.0
btw_uit = float(exp_df["btw"].sum())   if not exp_df.empty else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Omzet (ex BTW)",  f"€ {omzet:,.2f}")
c2.metric("Kosten (ex BTW)", f"€ {kosten:,.2f}")
c3.metric("Winst",           f"€ {omzet - kosten:,.2f}")
c4.metric("BTW saldo",       f"€ {btw_in - btw_uit:,.2f}",
          help="Positief = te betalen aan Belastingdienst")

st.divider()


def _derive_kwartaal(datum) -> int:
    try:
        return (pd.to_datetime(str(datum)).month - 1) // 3 + 1
    except Exception:
        return kw_num or 1


def _precompute_btw(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute ex_btw and btw from total + btw_pct so disabled columns show correct values."""
    df = df.copy()
    pct = df["btw_pct"].apply(lambda x: int(x or 0))
    tot = df["total"].apply(lambda x: float(x or 0))
    df["ex_btw"] = (tot / (1 + pct / 100)).where(pct > 0, tot).round(2)
    df["btw"]    = (tot - df["ex_btw"]).round(2)
    return df


def _format_bankboeking(info: dict) -> str:
    if not info:
        return ""
    d = pd.to_datetime(info.get("datum"), errors="coerce")
    d_txt = d.strftime("%d-%m-%Y") if pd.notna(d) else str(info.get("datum") or "")
    bedrag = float(info.get("bedrag") or 0)
    naam = str(info.get("naam") or "")
    return f"{d_txt} | EUR {bedrag:,.2f} | {naam}"


def _totals_row(edited_df: pd.DataFrame, money_cols: list[str],
                all_cols: list[str], col_cfg: dict, label_col: str = "naam") -> None:
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
    st.dataframe(pd.DataFrame([row]), column_config=col_cfg, use_container_width=True, hide_index=True)


# ── Inkomsten ─────────────────────────────────────────────────────────────────

st.subheader("📥 Inkomsten")
st.caption("Voer Totaal en BTW% in; Ex BTW en BTW worden automatisch berekend. Betaald wordt beheerd via bank.")

inc_cols = ["factuur", "naam", "datum", "project", "btw_pct", "total", "ex_btw", "btw", "betaald"]
inc_data_cols = ["id"] + inc_cols
inc_display = inc_df[inc_data_cols].copy() if not inc_df.empty else pd.DataFrame(columns=inc_data_cols)

# Auto-check betaald for bank-matched rows
if "id" in inc_df.columns and not inc_display.empty:
    inc_display.loc[inc_df["id"].isin(matched_inc_ids).values, "betaald"] = True

inc_display = _precompute_btw(inc_display)
inc_display = inc_display.set_index("id", drop=True)

inc_col_cfg = {
    "factuur":  st.column_config.TextColumn(     "Factuur", width="small"),
    "naam":     st.column_config.TextColumn(     "Klant",   width="medium"),
    "datum":    st.column_config.DateColumn(     "Datum",   format="DD-MM-YYYY",  width="small"),
    "project":  st.column_config.TextColumn(     "Project", width="medium"),
    "btw_pct":  st.column_config.SelectboxColumn("BTW %",   options=[0, 9, 21],   width="small"),
    "total":    st.column_config.NumberColumn(   "Totaal",  format="€ %.2f",      width="small"),
    "ex_btw":   st.column_config.NumberColumn(   "Ex BTW",  format="€ %.2f",      width="small",  disabled=True),
    "btw":      st.column_config.NumberColumn(   "BTW",     format="€ %.2f",      width="small",  disabled=True),
    "betaald":  st.column_config.CheckboxColumn( "Betaald",                        width="small",  disabled=True),
}

inc_edited = st.data_editor(
    inc_display, column_config=inc_col_cfg,
    num_rows="dynamic", use_container_width=True, hide_index=True,
    key=f"inc_{jaar}_{kw_label}",
)
_totals_row(inc_edited, ["total", "ex_btw", "btw"], inc_cols, inc_col_cfg, label_col="naam")

if st.button("💾 Inkomsten opslaan", type="primary", key="save_inc"):
    to_save = inc_edited.copy()
    to_save["id"] = pd.to_numeric(to_save.index, errors="coerce")
    to_save["kwartaal"] = to_save["datum"].apply(_derive_kwartaal)
    save_income(to_save, jaar, kw_num)
    st.success("Inkomsten opgeslagen.")
    st.rerun()

st.divider()

# ── Uitgaven ──────────────────────────────────────────────────────────────────

st.subheader("📤 Uitgaven")
st.caption("Voer Totaal en BTW% in; Ex BTW en BTW worden automatisch berekend. Afgerekend wordt beheerd via bank.")

exp_cols = ["factuur", "naam", "datum", "categorie", "btw_pct", "total", "ex_btw", "btw", "afgerekend"]
exp_data_cols = ["id"] + exp_cols
exp_display_full = exp_df[exp_data_cols].copy() if not exp_df.empty else pd.DataFrame(columns=exp_data_cols)

# Auto-check afgerekend for bank-matched rows
if "id" in exp_df.columns and not exp_display_full.empty:
    exp_display_full.loc[exp_df["id"].isin(matched_exp_ids).values, "afgerekend"] = True

exp_display_full = _precompute_btw(exp_display_full)

# Default sort by factuurnummer
if not exp_display_full.empty:
    exp_display_full = exp_display_full.sort_values("factuur", kind="stable").reset_index(drop=True)
    if "id" in exp_df.columns:
        exp_df = exp_df.sort_values("factuur", kind="stable").reset_index(drop=True)

exp_display_full["bankboeking"] = ""
if "id" in exp_df.columns and not exp_display_full.empty:
    expense_ids = exp_df["id"].reset_index(drop=True)
    exp_display_full["bankboeking"] = expense_ids.apply(
        lambda eid: _format_bankboeking(bank_info_by_expense_id.get(int(eid))) if pd.notna(eid) else ""
    )

col_fn, col_fc = st.columns([2, 2])
filter_naam = col_fn.text_input("Filter op naam", key="exp_naam_filter", placeholder="Type om te filteren…")
filter_cat  = col_fc.selectbox("Filter op categorie", ["Alle"] + categories, key="exp_cat_filter")

exp_display = exp_display_full.copy()
if filter_naam:
    exp_display = exp_display[exp_display["naam"].str.contains(filter_naam, case=False, na=False)]
if filter_cat != "Alle":
    exp_display = exp_display[exp_display["categorie"] == filter_cat]
exp_display = exp_display.copy()
exp_display = exp_display.set_index("id", drop=True)

visible_ids = set(exp_display.index.dropna().astype(int)) if not exp_display.empty else set()

exp_col_cfg = {
    "factuur":    st.column_config.TextColumn(     "Factuur",    width="small"),
    "naam":       st.column_config.TextColumn(     "Naam",       width="medium"),
    "datum":      st.column_config.DateColumn(     "Datum",      format="DD-MM-YYYY",   width="small"),
    "categorie":  st.column_config.SelectboxColumn("Categorie",  options=categories,    width="medium"),
    "btw_pct":    st.column_config.SelectboxColumn("BTW %",      options=[0, 9, 21],    width="small"),
    "total":      st.column_config.NumberColumn(   "Totaal",     format="€ %.2f",       width="small"),
    "ex_btw":     st.column_config.NumberColumn(   "Ex BTW",     format="€ %.2f",       width="small",  disabled=True),
    "btw":        st.column_config.NumberColumn(   "BTW",        format="€ %.2f",       width="small",  disabled=True),
    "bankboeking": st.column_config.TextColumn(    "Bankboeking",                      width="large"),
    "afgerekend": st.column_config.CheckboxColumn( "Afgerekend",                        width="small",  disabled=True),
}

exp_edited = st.data_editor(
    exp_display, column_config=exp_col_cfg,
    num_rows="dynamic", use_container_width=True, hide_index=True,
    disabled=["ex_btw", "btw", "bankboeking", "afgerekend"],
    key=f"exp_{jaar}_{kw_label}_{filter_naam}_{filter_cat}",
)
_totals_row(exp_edited, ["total", "ex_btw", "btw"], exp_cols + ["bankboeking"], exp_col_cfg, label_col="naam")

with st.expander("🔎 Details gekoppelde bankboekingen", expanded=False):
    if "id" in exp_df.columns and not exp_display.empty:
        visible_meta = exp_display.reset_index()[["id", "factuur", "naam", "datum", "total"]].copy()
        visible_meta = visible_meta[visible_meta["id"].notna()]
        linked_rows = []
        for _, row in visible_meta.iterrows():
            exp_id = int(row["id"])
            info = bank_info_by_expense_id.get(exp_id)
            if info:
                linked_rows.append((row, info))

        if not linked_rows:
            st.info("Geen gekoppelde bankboekingen in de huidige selectie.")
        else:
            for row, info in linked_rows:
                factuur = str(row.get("factuur") or "")
                naam = str(row.get("naam") or "")
                datum = row.get("datum")
                datum_txt = pd.to_datetime(datum, errors="coerce")
                if pd.notna(datum_txt):
                    datum_label = datum_txt.strftime("%d-%m-%Y")
                else:
                    datum_label = str(datum or "")
                total = float(row.get("total") or 0)
                label = f"{factuur} | {datum_label} | {naam} | € {total:,.2f}"
                with st.expander(label, expanded=False):
                    d = pd.to_datetime(info.get("datum"), errors="coerce")
                    d_txt = d.strftime("%d-%m-%Y") if pd.notna(d) else str(info.get("datum") or "")
                    st.write(f"Naam banktransactie: {info.get('naam') or ''}")
                    st.write(f"IBAN: {info.get('iban') or ''}")
                    st.write(f"Datum: {d_txt}")
                    st.write(f"Bedrag: EUR {float(info.get('bedrag') or 0):,.2f}")

                    tx_id = int(info["tx_id"])
                    if st.button("Ontkoppelen", key=f"unlink_exp_tx_{tx_id}"):
                        unlink_bank_transaction(tx_id)
                        st.success("Bankkoppeling verwijderd.")
                        st.rerun()
    else:
        st.info("Geen zichtbare uitgavenregels om details te tonen.")

if st.button("💾 Uitgaven opslaan", type="primary", key="save_exp"):
    exp_to_save = exp_edited.drop(columns=["bankboeking"], errors="ignore")
    exp_to_save["id"] = pd.to_numeric(exp_to_save.index, errors="coerce")
    filter_active = bool(filter_naam) or filter_cat != "Alle"
    if filter_active and visible_ids:
        fresh = get_expenses(jaar, kw_num)
        unchanged = fresh[~fresh["id"].isin(visible_ids)]
        final = pd.concat([unchanged[["id"] + exp_cols], exp_to_save[["id"] + exp_cols]], ignore_index=True)
    else:
        final = exp_to_save[["id"] + exp_cols]
    final["kwartaal"] = final["datum"].apply(_derive_kwartaal)
    save_expenses(final, jaar, kw_num)
    st.success("Uitgaven opgeslagen.")
    st.rerun()
