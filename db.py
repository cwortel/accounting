import sqlite3
import pandas as pd
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent / "data" / "boekhouding.db"

DEFAULT_CATEGORIES = [
    "Administration",
    "Car Expenses",
    "Office",
    "Representation",
    "Travel",
    "Other",
]


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                factuur     TEXT    NOT NULL DEFAULT '',
                naam        TEXT    NOT NULL DEFAULT '',
                datum       TEXT    NOT NULL DEFAULT '',
                categorie   TEXT    NOT NULL DEFAULT '',
                btw_pct     INTEGER NOT NULL DEFAULT 0,
                btw         REAL    NOT NULL DEFAULT 0,
                ex_btw      REAL    NOT NULL DEFAULT 0,
                total       REAL    NOT NULL DEFAULT 0,
                afgerekend  INTEGER NOT NULL DEFAULT 0,
                jaar        INTEGER NOT NULL,
                kwartaal    INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS income (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                factuur     TEXT    NOT NULL DEFAULT '',
                naam        TEXT    NOT NULL DEFAULT '',
                datum       TEXT    NOT NULL DEFAULT '',
                project     TEXT    NOT NULL DEFAULT '',
                btw_pct     INTEGER NOT NULL DEFAULT 21,
                btw         REAL    NOT NULL DEFAULT 0,
                ex_btw      REAL    NOT NULL DEFAULT 0,
                total       REAL    NOT NULL DEFAULT 0,
                betaald     INTEGER NOT NULL DEFAULT 0,
                jaar        INTEGER NOT NULL,
                kwartaal    INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS categories (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                naam TEXT    NOT NULL UNIQUE
            );
        """)
        for cat in DEFAULT_CATEGORIES:
            conn.execute("INSERT OR IGNORE INTO categories (naam) VALUES (?)", (cat,))
        conn.commit()


def get_categories() -> list:
    with get_connection() as conn:
        rows = conn.execute("SELECT naam FROM categories ORDER BY naam").fetchall()
    return [r["naam"] for r in rows]


def _to_date(val):
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return pd.to_datetime(str(val)[:10]).date()
    except Exception:
        return None


def _date_str(val) -> str:
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass
    return str(val)[:10]


def _safe_int(val, default: int = 0) -> int:
    try:
        if val is None:
            return default
        if isinstance(val, float) and pd.isna(val):
            return default
        return int(float(str(val)))
    except (TypeError, ValueError):
        return default


def _safe_float(val, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        if isinstance(val, float) and pd.isna(val):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_bool(val) -> int:
    try:
        if val is None:
            return 0
        if isinstance(val, float) and pd.isna(val):
            return 0
        return int(bool(val))
    except (TypeError, ValueError):
        return 0


# ── Expenses ──────────────────────────────────────────────────────────────────

def get_expenses(jaar: int, kwartaal: int = None) -> pd.DataFrame:
    sql = "SELECT * FROM expenses WHERE jaar = ?"
    params = [jaar]
    if kwartaal:
        sql += " AND kwartaal = ?"
        params.append(kwartaal)
    sql += " ORDER BY datum, factuur"
    with get_connection() as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "factuur", "naam", "datum", "categorie",
            "btw_pct", "btw", "ex_btw", "total", "afgerekend", "jaar", "kwartaal",
        ])
    df["datum"] = df["datum"].apply(_to_date)
    df["afgerekend"] = df["afgerekend"].astype(bool)
    df["btw_pct"] = df["btw_pct"].astype(int)
    return df


def save_expenses(df: pd.DataFrame, jaar: int, kwartaal: int = None) -> None:
    with get_connection() as conn:
        if kwartaal:
            conn.execute("DELETE FROM expenses WHERE jaar=? AND kwartaal=?", (jaar, kwartaal))
        else:
            conn.execute("DELETE FROM expenses WHERE jaar=?", (jaar,))
        for _, row in df.iterrows():
            naam = str(row.get("naam") or "").strip()
            factuur = str(row.get("factuur") or "").strip()
            if not naam and not factuur:
                continue
            total = round(_safe_float(row.get("total")), 2)
            btw_pct = _safe_int(row.get("btw_pct"))
            # Derive ex_btw and btw from total (total is the primary input field)
            ex_btw = round(total / (1 + btw_pct / 100), 2) if btw_pct > 0 else total
            btw = round(total - ex_btw, 2)
            row_q = _safe_int(row.get("kwartaal"), kwartaal or 1)
            conn.execute(
                "INSERT INTO expenses "
                "(factuur,naam,datum,categorie,btw_pct,btw,ex_btw,total,afgerekend,jaar,kwartaal) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    factuur, naam,
                    _date_str(row.get("datum")),
                    str(row.get("categorie") or ""),
                    btw_pct, btw, ex_btw, total,
                    _safe_bool(row.get("afgerekend")),
                    jaar, row_q,
                ),
            )
        conn.commit()


# ── Income ────────────────────────────────────────────────────────────────────

def get_income(jaar: int, kwartaal: int = None) -> pd.DataFrame:
    sql = "SELECT * FROM income WHERE jaar = ?"
    params = [jaar]
    if kwartaal:
        sql += " AND kwartaal = ?"
        params.append(kwartaal)
    sql += " ORDER BY datum, factuur"
    with get_connection() as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "factuur", "naam", "datum", "project",
            "btw_pct", "btw", "ex_btw", "total", "betaald", "jaar", "kwartaal",
        ])
    df["datum"] = df["datum"].apply(_to_date)
    df["betaald"] = df["betaald"].astype(bool)
    df["btw_pct"] = df["btw_pct"].astype(int)
    return df


def save_income(df: pd.DataFrame, jaar: int, kwartaal: int = None) -> None:
    with get_connection() as conn:
        if kwartaal:
            conn.execute("DELETE FROM income WHERE jaar=? AND kwartaal=?", (jaar, kwartaal))
        else:
            conn.execute("DELETE FROM income WHERE jaar=?", (jaar,))
        for _, row in df.iterrows():
            naam = str(row.get("naam") or "").strip()
            factuur = str(row.get("factuur") or "").strip()
            if not naam and not factuur:
                continue
            ex_btw = round(_safe_float(row.get("ex_btw")), 2)
            btw_pct = _safe_int(row.get("btw_pct"), 21)
            btw = round(ex_btw * btw_pct / 100, 2)
            total = round(ex_btw + btw, 2)
            row_q = _safe_int(row.get("kwartaal"), kwartaal or 1)
            conn.execute(
                "INSERT INTO income "
                "(factuur,naam,datum,project,btw_pct,btw,ex_btw,total,betaald,jaar,kwartaal) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    factuur, naam,
                    _date_str(row.get("datum")),
                    str(row.get("project") or ""),
                    btw_pct, btw, ex_btw, total,
                    _safe_bool(row.get("betaald")),
                    jaar, row_q,
                ),
            )
        conn.commit()


# ── Summary queries ───────────────────────────────────────────────────────────

def get_yearly_summary(jaar: int) -> pd.DataFrame:
    with get_connection() as conn:
        inc = pd.read_sql_query(
            "SELECT kwartaal, SUM(ex_btw) as omzet, SUM(btw) as btw_in "
            "FROM income WHERE jaar=? GROUP BY kwartaal",
            conn, params=[jaar],
        )
        exp = pd.read_sql_query(
            "SELECT kwartaal, SUM(ex_btw) as kosten, SUM(btw) as btw_uit "
            "FROM expenses WHERE jaar=? GROUP BY kwartaal",
            conn, params=[jaar],
        )
    base = pd.DataFrame({"kwartaal": [1, 2, 3, 4]})
    df = base.merge(inc, on="kwartaal", how="left").merge(exp, on="kwartaal", how="left").fillna(0)
    df["winst"] = df["omzet"] - df["kosten"]
    df["btw_saldo"] = df["btw_in"] - df["btw_uit"]
    return df


def get_expense_by_category(jaar: int) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT categorie, SUM(ex_btw) as totaal FROM expenses "
            "WHERE jaar=? GROUP BY categorie ORDER BY totaal DESC",
            conn, params=[jaar],
        )


# ── Bank transactions ─────────────────────────────────────────────────────────

def _init_bank_table(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bank_transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            datum       TEXT    NOT NULL,
            bedrag      REAL    NOT NULL,
            naam        TEXT    NOT NULL DEFAULT '',
            iban        TEXT    NOT NULL DEFAULT '',
            referentie  TEXT    NOT NULL DEFAULT '',
            bestand     TEXT    NOT NULL DEFAULT '',
            jaar        INTEGER NOT NULL,
            kwartaal    INTEGER NOT NULL,
            expense_id  INTEGER,
            income_id   INTEGER,
            fooi        REAL    NOT NULL DEFAULT 0,
            prive       INTEGER NOT NULL DEFAULT 0,
            prive_omschrijving TEXT NOT NULL DEFAULT ''
        );
    """)
    # Migration: add columns that may be missing in older databases
    for col, definition in [
        ("prive", "INTEGER NOT NULL DEFAULT 0"),
        ("prive_omschrijving", "TEXT NOT NULL DEFAULT ''"),
    ]:
        try:
            conn.execute(f"ALTER TABLE bank_transactions ADD COLUMN {col} {definition}")
            conn.commit()
        except sqlite3.OperationalError:
            pass


def import_camt(file_path: str) -> int:
    """Parse a CAMT.053 XML file and insert new transactions. Returns count added."""
    import xml.etree.ElementTree as ET

    tree = ET.parse(file_path)
    root = tree.getroot()
    # Support both .001.02 and .001.08 namespace variants
    ns_uri = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    ns = {"c": ns_uri} if ns_uri else {}

    def find(el, path):
        return el.findtext(f"c:{path}" if ns else path, namespaces=ns or None)

    def findp(el, path):
        return el.findtext(path.replace("c:", "") if not ns else path, namespaces=ns or None)

    filename = Path(file_path).name
    count = 0

    with get_connection() as conn:
        _init_bank_table(conn)
        existing = {row[0] for row in conn.execute(
            "SELECT datum || '_' || bedrag || '_' || iban FROM bank_transactions WHERE bestand=?",
            (filename,)
        ).fetchall()}

        entries = root.findall(".//c:Ntry", ns) if ns else root.findall(".//Ntry")
        for entry in entries:
            amt_raw = find(entry, "Amt") or "0"
            ind = find(entry, "CdtDbtInd") or "DBIT"
            bedrag = float(amt_raw) * (1 if ind == "CRDT" else -1)

            date_el = entry.find("c:BookgDt", ns) if ns else entry.find("BookgDt")
            datum = (find(date_el, "Dt") if date_el is not None else None) or ""

            detail = entry.find(".//c:TxDtls", ns) if ns else entry.find(".//TxDtls")
            src = detail if detail is not None else entry

            naam = (
                src.findtext(".//c:RltdPties/c:Dbtr/c:Pty/c:Nm", namespaces=ns)
                or src.findtext(".//c:RltdPties/c:Cdtr/c:Pty/c:Nm", namespaces=ns)
                or ""
            )
            iban = (
                src.findtext(".//c:RltdPties/c:DbtrAcct/c:Id/c:IBAN", namespaces=ns)
                or src.findtext(".//c:RltdPties/c:CdtrAcct/c:Id/c:IBAN", namespaces=ns)
                or ""
            )
            referentie = (
                src.findtext(".//c:RmtInf/c:Ustrd", namespaces=ns)
                or entry.findtext("c:AddtlNtryInf", namespaces=ns)
                or ""
            )

            if not datum:
                continue

            dedup_key = f"{datum}_{bedrag}_{iban}"
            if dedup_key in existing:
                continue

            try:
                d = pd.to_datetime(datum)
                jaar = d.year
                kwartaal = (d.month - 1) // 3 + 1
            except Exception:
                continue

            conn.execute(
                "INSERT INTO bank_transactions "
                "(datum,bedrag,naam,iban,referentie,bestand,jaar,kwartaal) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (datum, bedrag, naam, iban, referentie, filename, jaar, kwartaal),
            )
            existing.add(dedup_key)
            count += 1

        conn.commit()
    return count


def get_bank_transactions(jaar: int, kwartaal: int = None, only_unmatched: bool = False) -> pd.DataFrame:
    sql = "SELECT * FROM bank_transactions WHERE jaar=?"
    params = [jaar]
    if kwartaal:
        sql += " AND kwartaal=?"
        params.append(kwartaal)
    if only_unmatched:
        sql += " AND expense_id IS NULL AND income_id IS NULL AND prive=0"
    sql += " ORDER BY datum, id"
    with get_connection() as conn:
        _init_bank_table(conn)
        df = pd.read_sql_query(sql, conn, params=params)
    if not df.empty:
        df["datum"] = df["datum"].apply(_to_date)
    return df


def link_bank_transaction(tx_id: int, expense_id: int = None, income_id: int = None, fooi: float = 0.0) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bank_transactions SET expense_id=?, income_id=?, fooi=?, prive=0, prive_omschrijving='' WHERE id=?",
            (expense_id, income_id, round(fooi, 2), tx_id),
        )
        conn.commit()


def mark_bank_as_prive(tx_id: int, omschrijving: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bank_transactions SET prive=1, prive_omschrijving=?, expense_id=NULL, income_id=NULL, fooi=0 WHERE id=?",
            (omschrijving.strip(), tx_id),
        )
        conn.commit()


def unlink_bank_transaction(tx_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bank_transactions SET expense_id=NULL, income_id=NULL, fooi=0, prive=0, prive_omschrijving='' WHERE id=?",
            (tx_id,),
        )
        conn.commit()


def get_btw_by_quarter(jaar: int):
    with get_connection() as conn:
        inc = pd.read_sql_query(
            "SELECT kwartaal, btw_pct, SUM(ex_btw) as grondslag, SUM(btw) as btw "
            "FROM income WHERE jaar=? GROUP BY kwartaal, btw_pct",
            conn, params=[jaar],
        )
        exp = pd.read_sql_query(
            "SELECT kwartaal, SUM(btw) as aftrekbare_btw "
            "FROM expenses WHERE jaar=? GROUP BY kwartaal",
            conn, params=[jaar],
        )
    return inc, exp
