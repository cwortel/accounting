import streamlit as st
import pandas as pd
from db import init_db, get_expenses, save_expenses, get_categories

st.set_page_config(page_title="Uitgaven", page_icon="📤", layout="wide")
init_db()

st.title("📤 Uitgaven")

if "jaar" not in st.session_state:
    st.session_state["jaar"] = 2026

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024], key="jaar")
kw_label = st.sidebar.selectbox("Kwartaal", ["Alle", "Q1", "Q2", "Q3", "Q4"])
kw_num = None if kw_label == "Alle" else int(kw_label[1])

st.sidebar.divider()
st.sidebar.markdown("**Filters**")
filter_naam = st.sidebar.text_input("Naam (bevat)", "")
filter_totaal_str = st.sidebar.text_input("Totaal (€ geheel getal, bijv. 85)", "")

st.sidebar.divider()
st.sidebar.markdown("**Sortering**")
sort_col = st.sidebar.selectbox(
    "Kolom",
    ["factuur", "naam", "datum", "categorie", "total"],
    index=0,
    format_func={"factuur": "Factuur", "naam": "Naam", "datum": "Datum",
                 "categorie": "Categorie", "total": "Totaal"}.get,
)
sort_asc = st.sidebar.checkbox("Oplopend ↑", value=True)

categories = get_categories()


def to_dutch(val) -> str:
    """Format float as Dutch notation: 1234.56 → '1.234,56'"""
    try:
        v = float(val or 0)
    except (TypeError, ValueError):
        return "0,00"
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def from_dutch(val_str) -> float:
    """Parse Dutch notation string to float: '1.234,56' → 1234.56"""
    try:
        s = str(val_str or "").strip()
        s = s.replace(".", "").replace(",", ".")
        return float(s)
    except (TypeError, ValueError):
        return 0.0


# ── Load, filter, sort ────────────────────────────────────────────────────────

df = get_expenses(jaar, kw_num)

if filter_naam:
    df = df[df["naam"].str.contains(filter_naam, case=False, na=False)]

if filter_totaal_str.strip():
    try:
        target = int(filter_totaal_str.strip())
        df = df[df["total"].apply(lambda x: int(round(float(x or 0))) == target)]
    except ValueError:
        st.sidebar.warning("Voer een geheel getal in.")

# Track which IDs are visible (for safe save when filter is active)
visible_ids = set(df["id"].dropna().astype(int).tolist()) if "id" in df.columns else set()

if sort_col in df.columns and not df.empty:
    df = df.sort_values(sort_col, ascending=sort_asc, kind="stable")

# ── Build display DataFrame ───────────────────────────────────────────────────

show_cols = ["factuur", "naam", "datum", "categorie", "btw_pct",
             "total", "ex_btw", "btw", "afgerekend"]
if kw_num is None:
    show_cols = ["kwartaal"] + show_cols

display_df = df[show_cols].copy() if not df.empty else pd.DataFrame(columns=show_cols)

# Pre-compute ex_btw / btw from total for display (these columns are disabled)
if not display_df.empty:
    def _compute_ex(row):
        pct = int(row.get("btw_pct") or 0)
        tot = float(row.get("total") or 0)
        return round(tot / (1 + pct / 100), 2) if pct > 0 else tot

    display_df["ex_btw"] = display_df.apply(_compute_ex, axis=1)
    display_df["btw"] = display_df["total"].apply(lambda x: float(x or 0)) - display_df["ex_btw"]

# Format monetary columns as Dutch strings
for col in ["total", "ex_btw", "btw"]:
    if col in display_df.columns:
        display_df[col] = display_df[col].apply(to_dutch)

# ── Editor ────────────────────────────────────────────────────────────────────

col_config = {
    "kwartaal":   st.column_config.SelectboxColumn("Q",          options=[1, 2, 3, 4],   width="small"),
    "factuur":    st.column_config.TextColumn(      "Factuur",    width="small"),
    "naam":       st.column_config.TextColumn(      "Naam",       width="medium"),
    "datum":      st.column_config.DateColumn(      "Datum",      format="DD-MM-YYYY",   width="small"),
    "categorie":  st.column_config.SelectboxColumn( "Categorie",  options=categories,    width="medium"),
    "btw_pct":    st.column_config.SelectboxColumn( "BTW %",      options=[0, 9, 21],    width="small"),
    "total":      st.column_config.TextColumn(      "Totaal",     width="small",
                                                    help="Voer het totaalbedrag in (incl. BTW), bijv. 1.234,56"),
    "ex_btw":     st.column_config.TextColumn(      "Ex BTW",     width="small"),
    "btw":        st.column_config.TextColumn(      "BTW",        width="small"),
    "afgerekend": st.column_config.CheckboxColumn(  "Afgerekend",                        width="small"),
}

filter_active = bool(filter_naam) or bool(filter_totaal_str.strip())
if filter_active:
    st.info(
        f"Filter actief — {len(df)} rij(en) zichtbaar. "
        "Opslaan werkt alleen op de zichtbare rijen; overige rijen blijven bewaard."
    )

st.caption(
    "Voer **Totaal** in (incl. BTW, komma als decimaalteken: **1.234,56**). "
    "Ex BTW en BTW worden automatisch berekend bij opslaan. "
    "Sorteren via de zijbalk — kolomkopjes zijn niet klikbaar in het bewerkraster."
)

edited = st.data_editor(
    display_df,
    column_config=col_config,
    disabled=["ex_btw", "btw"],
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key=f"exp_{jaar}_{kw_label}_{sort_col}_{sort_asc}",
)

# ── Totals bar ────────────────────────────────────────────────────────────────

if not edited.empty:
    ex = edited["ex_btw"].apply(from_dutch).sum()
    btw_sum = edited["btw"].apply(from_dutch).sum()
    tot = edited["total"].apply(from_dutch).sum()
    st.info(
        f"Totaal ex BTW: **€ {to_dutch(ex)}** &nbsp;|&nbsp; "
        f"BTW: **€ {to_dutch(btw_sum)}** &nbsp;|&nbsp; "
        f"Incl. BTW: **€ {to_dutch(tot)}**"
    )

# ── Save ──────────────────────────────────────────────────────────────────────

if st.button("💾 Opslaan", type="primary"):
    save_edit = edited.copy()

    # Parse Dutch format strings back to floats
    for col in ["total", "ex_btw", "btw"]:
        if col in save_edit.columns:
            save_edit[col] = save_edit[col].apply(from_dutch)

    if "kwartaal" not in save_edit.columns:
        save_edit["kwartaal"] = kw_num

    # When filter is active: merge edited rows back with unchanged rows to avoid data loss
    if filter_active and visible_ids:
        fresh = get_expenses(jaar, kw_num)
        unchanged = fresh[~fresh["id"].isin(visible_ids)]
        final_df = pd.concat([unchanged, save_edit], ignore_index=True)
    else:
        final_df = save_edit

    save_expenses(final_df, jaar, kw_num)
    st.success("Opgeslagen!")
    st.rerun()
