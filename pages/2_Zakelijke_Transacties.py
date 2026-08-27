import streamlit as st
import pandas as pd
from pathlib import Path
from db import (
    init_db, import_camt, import_rabobank_csv, get_bank_transactions,
    get_expenses, get_income, link_bank_transaction, unlink_bank_transaction,
    mark_bank_as_prive, mark_bank_as_intern, mark_bank_as_btw_betaling,
    get_rekeningen, get_categories, create_expense_from_bank_transaction,
)

st.set_page_config(page_title="Zakelijke Transacties", page_icon="🏦", layout="wide")
init_db()


def _score_expense(exp_row, amt: float, tx_datum, tx_naam: str, tx_ref: str) -> int:
    """Score an expense as a match candidate. Returns -1 if disqualified."""
    exp_total = float(exp_row.get("total") or 0)
    if exp_total <= 0:
        return -1
    ratio = amt / exp_total
    # Disqualify: bank paid less than 95% or tip would exceed 25%
    if ratio < 0.95 or ratio > 1.25:
        return -1

    score = 0
    near_exact_amount = ratio <= 1.005

    # Amount: near-exact match scores highest; large tip scores low
    if near_exact_amount:
        score += 10
    elif ratio <= 1.10:
        score += 6
    elif ratio <= 1.20:
        score += 2
    else:
        score += 0  # 20-25% tip: allowed but unlikely

    # Date proximity: receipts are typically paid same day or within a week
    days = None
    try:
        exp_date = pd.to_datetime(str(exp_row["datum"])).date()
        days = abs((tx_datum - exp_date).days)
        if days == 0:
            score += 10
        elif days <= 2:
            score += 7
        elif days <= 7:
            score += 3
        elif days <= 14:
            score += 1
    except Exception:
        pass

    # Name: supplier name in bank naam or referentie (case-insensitive)
    hay = (str(tx_naam) + " " + str(tx_ref)).lower()
    exp_naam = str(exp_row.get("naam") or "").lower().strip()
    name_score = 0
    if exp_naam and exp_naam in hay:
        name_score = 10
    else:
        # Try longest word ≥4 chars from expense name
        words = sorted([w for w in exp_naam.split() if len(w) >= 4], key=len, reverse=True)
        if words and words[0] in hay:
            name_score = 5

    score += name_score

    if days is not None and days > 14:
        # Allow a wider window for recurring invoices when amount is exact and name strongly matches.
        if near_exact_amount and name_score >= 5 and days <= 35:
            if days <= 21:
                score += 1
            else:
                score += 0
        else:
            return -1  # dates too far apart

    return score


def _score_income(inc_row, amt: float, tx_datum, tx_naam: str, tx_ref: str) -> int:
    """Score an income entry as a match for a credit transaction."""
    inc_total = float(inc_row.get("total") or 0)
    if inc_total <= 0:
        return -1
    ratio = amt / inc_total
    # Credits should be close to invoice total (no tips on income)
    if ratio < 0.95 or ratio > 1.05:
        return -1

    score = 0
    if ratio <= 1.005:
        score += 10
    else:
        score += 4

    try:
        inc_date = pd.to_datetime(str(inc_row["datum"])).date()
        days = abs((tx_datum - inc_date).days)
        if days <= 7:
            score += 10
        elif days <= 30:
            score += 5
        elif days <= 60:
            score += 1
        else:
            return -1
    except Exception:
        pass

    hay = (str(tx_naam) + " " + str(tx_ref)).lower()
    inc_naam = str(inc_row.get("naam") or "").lower().strip()
    if inc_naam and inc_naam in hay:
        score += 10
    else:
        words = sorted([w for w in inc_naam.split() if len(w) >= 4], key=len, reverse=True)
        if words and words[0] in hay:
            score += 5

    return score

def _transfer_from_to(tx, rekening_names: dict) -> dict:
    bedrag = float(tx.get("bedrag") or 0)
    eigen_iban = str(tx.get("rekening") or "").strip()
    tegen_iban = str(tx.get("iban") or "").strip()

    eigen_naam = str(rekening_names.get(eigen_iban) or "Eigen rekening")
    tegen_naam_default = str(tx.get("naam") or "Tegenrekening")
    tegen_naam = str(rekening_names.get(tegen_iban) or tegen_naam_default)

    if bedrag < 0:
        van_naam, van_iban = eigen_naam, eigen_iban or "—"
        naar_naam, naar_iban = tegen_naam, tegen_iban or "—"
    else:
        van_naam, van_iban = tegen_naam, tegen_iban or "—"
        naar_naam, naar_iban = eigen_naam, eigen_iban or "—"

    if eigen_iban and tegen_iban:
        intern_label = f"{eigen_iban} > {tegen_iban}" if bedrag < 0 else f"{eigen_iban} < {tegen_iban}"
    else:
        intern_label = f"{van_iban} > {naar_iban}" if bedrag < 0 else f"{naar_iban} < {van_iban}"

    return {
        "van_naam": van_naam,
        "van_iban": van_iban,
        "naar_naam": naar_naam,
        "naar_iban": naar_iban,
        "intern_label": intern_label,
    }


BANK_DIR = Path(__file__).parent.parent / "data" / "BankTransactions"

st.title("🏦 Banktransacties")

if "jaar" not in st.session_state:
    st.session_state["jaar"] = 2026

jaar = st.sidebar.selectbox("Jaar", [2026, 2025, 2024], key="jaar")
kw_label = st.sidebar.selectbox("Kwartaal", ["Alle", "Q1", "Q2", "Q3", "Q4"])
kw_num = None if kw_label == "Alle" else int(kw_label[1])
only_unmatched = st.sidebar.checkbox("Alleen ongekoppeld", value=False)
naam_filter = st.sidebar.text_input("🔍 Filter op naam", "").strip().lower()
cat_filter = st.sidebar.selectbox(
    "Categorie",
    ["Alle", "Uitgave", "Inkomst", "Interne overboeking", "Privé onttrekking", "BTW betaling", "Ongekoppeld"],
)

# Always filter to business accounts only
BETALINGS_IBAN = "NL84RABO0188971130"
SPAAR_IBAN = "NL49RABO3161681290"
ZAKELIJK_IBANS = [BETALINGS_IBAN, SPAAR_IBAN]

# ── Import ─────────────────────────────────────────────────────────────────────
with st.expander("📂 Importeer bestanden", expanded=False):
    xml_files = sorted(BANK_DIR.glob("*.xml")) if BANK_DIR.exists() else []
    csv_files = sorted(BANK_DIR.glob("*.csv")) if BANK_DIR.exists() else []
    files = xml_files + csv_files
    if files:
        st.write(f"Gevonden in `{BANK_DIR}`:")
        for f in files:
            st.code(f"{f.name} ({'CAMT' if f.suffix == '.xml' else 'CSV'})")
        if st.button("⬆️ Importeer alle bestanden", type="primary"):
            total = 0
            for f in xml_files:
                n = import_camt(str(f))
                total += n
                st.write(f"  `{f.name}` → {n} nieuwe transacties")
            for f in csv_files:
                n = import_rabobank_csv(str(f))
                total += n
                st.write(f"  `{f.name}` → {n} nieuwe transacties")
            st.success(f"Totaal {total} transacties geïmporteerd.")
            st.rerun()
    else:
        st.info(f"Geen bestanden gevonden in `{BANK_DIR}`")

st.divider()

# ── Transaction list ───────────────────────────────────────────────────────────
df = get_bank_transactions(jaar, kw_num, only_unmatched)
df = df[df["rekening"].isin(ZAKELIJK_IBANS)] if not df.empty else df

if not df.empty and naam_filter:
    df = df[df["naam"].str.lower().str.contains(naam_filter, na=False)]

if not df.empty and cat_filter != "Alle":
    intern_col = df["intern"].astype(bool) if "intern" in df.columns else pd.Series(False, index=df.index)
    prive_col = df["prive"].astype(bool) if "prive" in df.columns else pd.Series(False, index=df.index)
    btw_col = df["btw_betaling"].astype(bool) if "btw_betaling" in df.columns else pd.Series(False, index=df.index)
    if cat_filter == "Uitgave":
        df = df[df["expense_id"].notna()]
    elif cat_filter == "Inkomst":
        df = df[df["income_id"].notna()]
    elif cat_filter == "Interne overboeking":
        df = df[intern_col]
    elif cat_filter == "Privé onttrekking":
        df = df[prive_col]
    elif cat_filter == "BTW betaling":
        df = df[btw_col]
    elif cat_filter == "Ongekoppeld":
        df = df[df["expense_id"].isna() & df["income_id"].isna() & ~intern_col & ~prive_col & ~btw_col]

if df.empty:
    st.info("Geen transacties gevonden. Importeer eerst een CAMT.053 bestand.")
    st.stop()

matched = df["expense_id"].notna() | df["income_id"].notna()
is_prive = df.get("prive", pd.Series(0, index=df.index)).astype(bool)
is_intern = df.get("intern", pd.Series(0, index=df.index)).astype(bool)
is_btw = df.get("btw_betaling", pd.Series(0, index=df.index)).astype(bool)
n_matched = matched.sum()
n_prive = is_prive.sum()
n_intern = is_intern.sum()
n_btw = is_btw.sum()
n_total = len(df)
df_betaal = df[df["rekening"] == BETALINGS_IBAN].copy()
df_spaar = df[df["rekening"] == SPAAR_IBAN].copy()
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Transacties", n_total)
c2.metric("Gekoppeld", int(n_matched))
c3.metric("Privé onttrekking", int(n_prive))
c4.metric("Intern", int(n_intern))
c5.metric("BTW betaling", int(n_btw))
c6.metric("Betaal/Spaar", f"{len(df_betaal)}/{len(df_spaar)}")

st.divider()

# Load expenses and income from current year + adjacent years so cross-year payments can be matched
all_exp = pd.concat([get_expenses(jaar - 1), get_expenses(jaar), get_expenses(jaar + 1)], ignore_index=True)
all_inc = pd.concat([get_income(jaar - 1),   get_income(jaar),   get_income(jaar + 1)],   ignore_index=True)
all_exp = all_exp.dropna(subset=["id"])
all_inc = all_inc.dropna(subset=["id"])
categories = get_categories()
rekeningen_df = get_rekeningen()
rekening_names = {
    str(r.get("iban") or "").strip(): str(r.get("naam") or "").strip()
    for _, r in rekeningen_df.iterrows()
    if str(r.get("iban") or "").strip()
}

# ── Per-transaction rows ───────────────────────────────────────────────────────
def _render_transaction_rows(df_rows: pd.DataFrame, key_prefix: str) -> None:
    for _, tx in df_rows.iterrows():
        tx_id = int(tx["id"])
        key_base = f"{key_prefix}_{tx_id}"
        is_matched = pd.notna(tx.get("expense_id")) or pd.notna(tx.get("income_id"))
        is_prive_tx = bool(tx.get("prive"))
        is_intern_tx = bool(tx.get("intern"))
        is_btw_tx = bool(tx.get("btw_betaling"))
        btw_tx_jaar = int(tx["btw_betaling_jaar"]) if pd.notna(tx.get("btw_betaling_jaar")) else 0
        btw_tx_kw = int(tx["btw_betaling_kwartaal"]) if pd.notna(tx.get("btw_betaling_kwartaal")) else 0
        bedrag = tx["bedrag"]
        bedrag_str = f"€ {bedrag:+,.2f}"

        if is_intern_tx:
            col_status = "🔄"
        elif is_prive_tx:
            col_status = "🟡"
        elif is_btw_tx:
            col_status = "📘"
        elif is_matched:
            col_status = "🟢"
        elif bedrag < 0:
            col_status = "🔴"
        else:
            col_status = "🔵"
        label = f"{col_status} {tx['datum']}  {bedrag_str}  —  {tx['naam']}"
        if is_intern_tx and tx.get("intern_omschrijving"):
            label += f"  *(intern: {tx['intern_omschrijving']})*"
        elif is_prive_tx and tx.get("prive_omschrijving"):
            label += f"  *(privé: {tx['prive_omschrijving']})*"
        elif is_btw_tx:
            label += f"  *(BTW betaling Q{btw_tx_kw} {btw_tx_jaar})*"
        elif tx.get("fooi") and tx["fooi"] != 0:
            label += f"  *(fooi: € {tx['fooi']:.2f})*"

        with st.expander(label, expanded=False):
            c1, c2 = st.columns([3, 2])
            route = _transfer_from_to(tx, rekening_names)
            with c1:
                st.markdown(f"**Naam:** {tx['naam']}")
                st.markdown("**Van:**")
                st.markdown(route["van_naam"])
                st.markdown(route["van_iban"])
                st.markdown("**Naar:**")
                st.markdown(route["naar_naam"])
                st.markdown(route["naar_iban"])
                st.markdown(f"**Referentie:** {tx['referentie'] or '—'}")
                st.markdown(f"**Bedrag:** {bedrag_str} &nbsp; {'(Betaling)' if bedrag < 0 else '(Ontvangst)'}")
                if tx.get("fooi") and tx["fooi"] != 0:
                    st.markdown(f"**Fooi/privé:** € {tx['fooi']:.2f}")

            with c2:
                if is_intern_tx:
                    omschr = tx.get("intern_omschrijving") or ""
                    st.info(f"🔄 Interne overboeking: **{omschr or '—'}**")
                    if st.button("🔓 Ontkoppelen", key=f"unlink_{key_base}"):
                        unlink_bank_transaction(tx_id)
                        st.rerun()
                elif is_prive_tx:
                    omschr = tx.get("prive_omschrijving") or ""
                    st.warning(f"\U0001f7e1 Priv\u00e9 onttrekking: **{omschr or '\u2014'}**")
                    if st.button("\U0001f513 Ontkoppelen", key=f"unlink_{key_base}"):
                        unlink_bank_transaction(tx_id)
                        st.rerun()
                elif is_btw_tx:
                    st.info(f"📘 BTW betaling: **Q{btw_tx_kw} {btw_tx_jaar}** (€ {abs(bedrag):,.2f})")
                    if st.button("🔓 Ontkoppelen", key=f"unlink_{key_base}"):
                        unlink_bank_transaction(tx_id)
                        st.rerun()
                elif is_matched:
                    if pd.notna(tx.get("expense_id")):
                        matched_row = all_exp[all_exp["id"] == tx["expense_id"]]
                        if not matched_row.empty:
                            r = matched_row.iloc[0]
                            factuur = str(r.get("factuur") or "").strip()
                            factuur_str = f" · {factuur}" if factuur else ""
                            st.success(f"Gekoppeld aan uitgave: **{r['naam']}** · {r['datum']}{factuur_str} · € {r['total']:.2f}")
                    if pd.notna(tx.get("income_id")):
                        matched_row = all_inc[all_inc["id"] == tx["income_id"]]
                        if not matched_row.empty:
                            r = matched_row.iloc[0]
                            factuur = str(r.get("factuur") or "").strip()
                            factuur_str = f" · {factuur}" if factuur else ""
                            st.success(f"Gekoppeld aan inkomst: **{r['naam']}** · {r['datum']}{factuur_str} · € {r['total']:.2f}")
                    if st.button("🔓 Ontkoppelen", key=f"unlink_{key_base}"):
                        unlink_bank_transaction(tx_id)
                        st.rerun()
                else:
                    # Matching form
                    st.markdown("**Koppel aan:**")
                    default_type = "Inkomst" if bedrag > 0 else "Uitgave"
                    _MATCH_TYPES = ["Uitgave", "Inkomst", "Privé onttrekking", "Interne overboeking", "BTW betaling"]
                    match_type = st.radio(
                        "Type",
                        _MATCH_TYPES,
                        index=_MATCH_TYPES.index(default_type),
                        key=f"type_{key_base}",
                        horizontal=True,
                    )

                    if match_type == "Interne overboeking":
                        default_omschr = route["intern_label"]
                        st.caption(f"Van/Naar voor deze boeking: {route['van_iban']} → {route['naar_iban']}")
                        omschr = st.text_input(
                            "Omschrijving (optioneel)",
                            value=default_omschr,
                            key=f"intern_omschr_{key_base}",
                        )
                        if st.button("🔄 Markeer als Intern", key=f"intern_{key_base}", type="primary"):
                            mark_bank_as_intern(tx_id, omschr)
                            st.rerun()

                    elif match_type == "BTW betaling":
                        st.caption(f"Markeer deze betaling (€ {abs(bedrag):,.2f}) als voldoening van de BTW aangifte.")
                        btw_jaar_sel = st.selectbox("Jaar", [2026, 2025, 2024], key=f"btw_jaar_{key_base}")
                        btw_kw_sel = st.selectbox("Kwartaal", [1, 2, 3, 4],
                                                   format_func=lambda x: f"Q{x}",
                                                   key=f"btw_kw_{key_base}")
                        if st.button("📘 Markeer als BTW betaling", key=f"btw_{key_base}", type="primary"):
                            mark_bank_as_btw_betaling(tx_id, btw_jaar_sel, btw_kw_sel)
                            st.rerun()

                    elif match_type == "Privé onttrekking":
                        omschr = st.text_input(
                            "Omschrijving (optioneel)",
                            value="Privé onttrekking" if bedrag < 0 else "Privé storting",
                            key=f"prive_omschr_{key_base}",
                        )
                        if st.button("\U0001f7e1 Markeer als Privé", key=f"prive_{key_base}", type="primary"):
                            mark_bank_as_prive(tx_id, omschr)
                            st.rerun()

                    elif match_type == "Uitgave":
                        if not all_exp.empty:
                            amt = abs(bedrag)
                            tx_datum_val = tx["datum"] if hasattr(tx["datum"], "year") else None
                            tx_naam_val = str(tx.get("naam") or "")
                            tx_ref_val = str(tx.get("referentie") or "")

                            scored = []
                            for _, er in all_exp.iterrows():
                                s = _score_expense(er, amt, tx_datum_val, tx_naam_val, tx_ref_val)
                                if s >= 0:
                                    scored.append((s, er))
                            scored.sort(key=lambda x: -x[0])
                            candidates_rows = [r for _, r in scored[:8]]

                            if not candidates_rows:
                                st.info("Geen passende uitgaven gevonden (datum, bedrag of naam komen niet overeen).")
                            else:
                                candidates = pd.DataFrame(candidates_rows)
                                options = {
                                    f"{r['datum']} — {r['naam']} (€ {r['total']:.2f})": int(r["id"])
                                    for _, r in candidates.iterrows()
                                }
                                selected_label = st.selectbox(
                                    "Kies uitgave",
                                    options=list(options.keys()),
                                    key=f"sel_exp_{key_base}",
                                )
                                selected_id = options[selected_label]
                                selected_row = all_exp[all_exp["id"] == selected_id].iloc[0]
                                selected_total = float(selected_row["total"])

                                diff = round(abs(bedrag) - selected_total, 2)
                                fooi_val = 0.0
                                if diff > 0:
                                    st.warning(
                                        f"Banktransactie is € {diff:.2f} hoger dan de factuur. "
                                        f"Dit kan een fooi of privé-deel zijn."
                                    )
                                    fooi_val = st.number_input(
                                        "Fooi / privé bedrag (€)",
                                        min_value=0.0,
                                        max_value=float(abs(bedrag)),
                                        value=diff,
                                        step=0.01,
                                        key=f"fooi_{key_base}",
                                    )

                                if st.button("✅ Koppelen", key=f"link_exp_{key_base}", type="primary"):
                                    link_bank_transaction(tx_id, expense_id=selected_id, fooi=fooi_val)
                                    st.rerun()
                        else:
                            st.info("Geen uitgaven beschikbaar om aan te koppelen.")

                        st.markdown("---")
                        st.caption("Geen bon? Maak direct een nieuwe uitgave aan vanuit deze transactie.")
                        new_factuur = st.text_input("Factuur (optioneel)", key=f"new_exp_factuur_{key_base}")
                        new_naam = st.text_input("Naam uitgave", value=str(tx.get("naam") or ""), key=f"new_exp_naam_{key_base}")
                        new_cat = st.selectbox("Categorie", options=categories, key=f"new_exp_cat_{key_base}")
                        new_btw = st.selectbox("BTW %", options=[0, 9, 21], index=0, key=f"new_exp_btw_{key_base}")
                        new_note = st.text_input("Notitie (optioneel)", key=f"new_exp_note_{key_base}")
                        if st.button("➕ Nieuwe uitgave aanmaken", key=f"create_exp_{key_base}"):
                            try:
                                new_id = create_expense_from_bank_transaction(
                                    tx_id=tx_id,
                                    categorie=str(new_cat),
                                    btw_pct=int(new_btw),
                                    factuur=new_factuur,
                                    naam=new_naam,
                                    notitie=new_note,
                                )
                                st.success(f"Uitgave aangemaakt en gekoppeld (id {new_id}).")
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))

                    elif match_type == "Inkomst" and not all_inc.empty:
                        amt = abs(bedrag)
                        tx_datum_val = tx["datum"] if hasattr(tx["datum"], "year") else None
                        tx_naam_val = str(tx.get("naam") or "")
                        tx_ref_val = str(tx.get("referentie") or "")

                        scored = []
                        for _, ir in all_inc.iterrows():
                            s = _score_income(ir, amt, tx_datum_val, tx_naam_val, tx_ref_val)
                            if s >= 0:
                                scored.append((s, ir))
                        scored.sort(key=lambda x: -x[0])
                        candidates_rows = [r for _, r in scored[:8]]

                        if not candidates_rows:
                            st.info("Geen passende inkomsten gevonden.")
                        else:
                            candidates = pd.DataFrame(candidates_rows)
                            options = {
                                f"{r['datum']} — {r['naam']} (€ {r['total']:.2f})": int(r["id"])
                                for _, r in candidates.iterrows()
                            }
                            selected_label = st.selectbox(
                                "Kies inkomst",
                                options=list(options.keys()),
                                key=f"sel_inc_{key_base}",
                            )
                            selected_id = options[selected_label]

                            if st.button("✅ Koppelen", key=f"link_inc_{key_base}", type="primary"):
                                link_bank_transaction(tx_id, income_id=selected_id)
                                st.rerun()
                    else:
                        st.info("Geen uitgaven/inkomsten beschikbaar voor dit jaar.")


st.subheader("📌 Betaalrekening transacties")
if df_betaal.empty:
    st.info("Geen transacties op de betaalrekening in deze selectie.")
else:
    _render_transaction_rows(df_betaal, "betaal")

if not df_spaar.empty:
    st.divider()
    with st.expander(f"💾 Spaarrekening transacties ({len(df_spaar)})", expanded=False):
        st.caption("Minder relevant voor dagelijkse matching; meestal de spiegeling van de betaalrekening.")
        _render_transaction_rows(df_spaar, "spaar")
