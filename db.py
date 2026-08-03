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
    with get_connection() as conn:
        _init_prive_tables(conn)
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
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            datum              TEXT    NOT NULL,
            bedrag             REAL    NOT NULL,
            naam               TEXT    NOT NULL DEFAULT '',
            iban               TEXT    NOT NULL DEFAULT '',
            referentie         TEXT    NOT NULL DEFAULT '',
            bestand            TEXT    NOT NULL DEFAULT '',
            jaar               INTEGER NOT NULL,
            kwartaal           INTEGER NOT NULL,
            expense_id         INTEGER,
            income_id          INTEGER,
            fooi               REAL    NOT NULL DEFAULT 0,
            prive              INTEGER NOT NULL DEFAULT 0,
            prive_omschrijving TEXT    NOT NULL DEFAULT '',
            rekening           TEXT    NOT NULL DEFAULT '',
            saldo_na_trn       REAL,
            code               TEXT    NOT NULL DEFAULT '',
            machtigingskenmerk TEXT    NOT NULL DEFAULT '',
            incassant_id       TEXT    NOT NULL DEFAULT '',
            prive_categorie    TEXT    NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS rekeningen (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            naam           TEXT    NOT NULL DEFAULT '',
            iban           TEXT    NOT NULL DEFAULT '' UNIQUE,
            type           TEXT    NOT NULL DEFAULT 'prive',
            categorie      TEXT    NOT NULL DEFAULT 'betaalrekening',
            saldo          REAL    NOT NULL DEFAULT 0,
            laatste_update TEXT    NOT NULL DEFAULT ''
        );
    """)
    for col, definition in [
        ("prive",              "INTEGER NOT NULL DEFAULT 0"),
        ("prive_omschrijving", "TEXT NOT NULL DEFAULT ''"),
        ("rekening",           "TEXT NOT NULL DEFAULT ''"),
        ("saldo_na_trn",       "REAL"),
        ("code",               "TEXT NOT NULL DEFAULT ''"),
        ("machtigingskenmerk", "TEXT NOT NULL DEFAULT ''"),
        ("incassant_id",       "TEXT NOT NULL DEFAULT ''"),
        ("prive_categorie",    "TEXT NOT NULL DEFAULT ''"),
    ]:
        try:
            conn.execute(f"ALTER TABLE bank_transactions ADD COLUMN {col} {definition}")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    # Tag existing CAMT transactions with business IBAN
    conn.execute(
        "UPDATE bank_transactions SET rekening='NL84RABO0188971130' "
        "WHERE rekening='' AND bestand LIKE '%.xml'"
    )
    conn.commit()


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

        # Track the most recent CLBD per own-account IBAN across all statements
        latest_clbd: dict[str, float] = {}

        stmts = root.findall(".//c:Stmt", ns) if ns else root.findall(".//Stmt")
        for stmt in stmts:
            # Own account IBAN for this statement
            stmt_iban = (
                stmt.findtext(".//c:Acct/c:Id/c:IBAN", namespaces=ns)
                or stmt.findtext(".//Acct/Id/IBAN")
                or ""
            )

            # Collect the closing booked balance for this statement
            for bal in (stmt.findall("c:Bal", ns) if ns else stmt.findall("Bal")):
                code_el = bal.findtext(".//c:CdOrPrtry/c:Cd", namespaces=ns)
                if code_el == "CLBD" and stmt_iban:
                    try:
                        amt = float(bal.findtext("c:Amt", namespaces=ns) or 0)
                        ind = bal.findtext("c:CdtDbtInd", namespaces=ns) or "CRDT"
                        latest_clbd[stmt_iban] = amt if ind == "CRDT" else -amt
                    except (TypeError, ValueError):
                        pass

            for entry in (stmt.findall("c:Ntry", ns) if ns else stmt.findall("Ntry")):
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
                tx_code = (
                    src.findtext(".//c:BkTxCd/c:Prtry/c:Cd", namespaces=ns)
                    or src.findtext(".//c:BkTxCd/c:Domn/c:Cd", namespaces=ns)
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
                    "(datum,bedrag,naam,iban,referentie,bestand,jaar,kwartaal,rekening,code) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (datum, bedrag, naam, iban, referentie, filename, jaar, kwartaal, stmt_iban, tx_code),
                )
                existing.add(dedup_key)
                count += 1

        # Update rekening saldo from the latest CLBD found per account
        for iban_key, saldo in latest_clbd.items():
            conn.execute(
                "UPDATE rekeningen SET saldo=?, laatste_update=date('now') WHERE iban=?",
                (saldo, iban_key),
            )
        conn.commit()
    return count


def import_rabobank_csv(file_path: str) -> int:
    """Parse a Rabobank CSV export and insert new transactions. Returns count added."""
    import csv as _csv

    filename = Path(file_path).name
    count = 0

    with get_connection() as conn:
        _init_bank_table(conn)
        existing_volgnrs = {row[0] for row in conn.execute(
            "SELECT referentie FROM bank_transactions WHERE bestand=? AND saldo_na_trn IS NOT NULL",
            (filename,)
        ).fetchall()}
        # Volgnrs already imported but missing saldo_na_trn (pre-migration rows)
        needs_backfill = {row[0] for row in conn.execute(
            "SELECT referentie FROM bank_transactions WHERE bestand=? AND saldo_na_trn IS NULL",
            (filename,)
        ).fetchall()}

        with open(file_path, encoding="latin-1", newline="") as f:
            reader = _csv.DictReader(f)
            for row in reader:
                datum = row["Datum"].strip()
                if not datum:
                    continue
                bedrag_str = row["Bedrag"].strip().replace("+", "").replace(",", ".")
                try:
                    bedrag = float(bedrag_str)
                except ValueError:
                    continue
                eigen_iban = row["IBAN/BBAN"].strip()
                naam = (row["Naam tegenpartij"].strip()
                        or row["Naam uiteindelijke partij"].strip())
                iban = row["Tegenrekening IBAN/BBAN"].strip()
                volgnr = row["Volgnr"].strip()
                tx_code = row.get("Code", "").strip()
                machtiging = row.get("Machtigingskenmerk", "").strip()
                incassant = row.get("Incassant ID", "").strip()
                referentie = " ".join(filter(None, [
                    row.get("Omschrijving-1", "").strip(),
                    row.get("Omschrijving-2", "").strip(),
                    row.get("Omschrijving-3", "").strip(),
                    row.get("Betalingskenmerk", "").strip(),
                ])).strip()
                # Parse Dutch-format running balance: "+1.157,00" → 1157.0
                saldo_str = row.get("Saldo na trn", "").strip()
                saldo_na_trn = None
                if saldo_str:
                    try:
                        saldo_na_trn = float(
                            saldo_str.replace("+", "").replace(".", "").replace(",", ".")
                        )
                    except ValueError:
                        pass
                if volgnr and volgnr in existing_volgnrs:
                    continue
                # Back-fill saldo_na_trn for rows imported before this column existed
                if volgnr and volgnr in needs_backfill and saldo_na_trn is not None:
                    conn.execute(
                        "UPDATE bank_transactions SET saldo_na_trn=?,code=?,machtigingskenmerk=?,incassant_id=? "
                        "WHERE bestand=? AND referentie=?",
                        (saldo_na_trn, tx_code, machtiging, incassant, filename, volgnr),
                    )
                    needs_backfill.discard(volgnr)
                    continue
                try:
                    d = pd.to_datetime(datum)
                    jaar = d.year
                    kwartaal = (d.month - 1) // 3 + 1
                except Exception:
                    continue
                conn.execute(
                    "INSERT INTO bank_transactions "
                    "(datum,bedrag,naam,iban,referentie,bestand,jaar,kwartaal,rekening,"
                    "saldo_na_trn,code,machtigingskenmerk,incassant_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (datum, bedrag, naam, iban,
                     volgnr or referentie, filename, jaar, kwartaal, eigen_iban,
                     saldo_na_trn, tx_code, machtiging, incassant),
                )
                if volgnr:
                    existing_volgnrs.add(volgnr)
                count += 1
        # Update rekening saldo with the most recent balance (only where available)
        conn.execute("""
            UPDATE rekeningen SET
                saldo = (
                    SELECT saldo_na_trn FROM bank_transactions
                    WHERE rekening = rekeningen.iban
                      AND saldo_na_trn IS NOT NULL
                    ORDER BY datum DESC, id DESC LIMIT 1
                ),
                laatste_update = date('now')
            WHERE iban IN (SELECT DISTINCT rekening FROM bank_transactions WHERE bestand=?)
              AND (
                  SELECT saldo_na_trn FROM bank_transactions
                  WHERE rekening = rekeningen.iban AND saldo_na_trn IS NOT NULL
                  ORDER BY datum DESC, id DESC LIMIT 1
              ) IS NOT NULL
        """, (filename,))
        conn.commit()
    return count


# ── Rekeningen ────────────────────────────────────────────────────────────────

def get_rekeningen() -> pd.DataFrame:
    with get_connection() as conn:
        _init_bank_table(conn)
        df = pd.read_sql_query(
            "SELECT * FROM rekeningen ORDER BY type, categorie, naam", conn
        )
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "naam", "iban", "type", "categorie", "saldo", "laatste_update"
        ])
    return df


def save_rekeningen(df: pd.DataFrame) -> None:
    with get_connection() as conn:
        _init_bank_table(conn)
        existing_ids = {r[0] for r in conn.execute("SELECT id FROM rekeningen").fetchall()}
        seen_ids: set[int] = set()
        for _, row in df.iterrows():
            naam = str(row.get("naam") or "").strip()
            if not naam:
                continue
            row_id = _safe_int(row.get("id"), 0)
            vals = (
                naam,
                str(row.get("iban") or "").strip().upper(),
                str(row.get("type") or "prive"),
                str(row.get("categorie") or "betaalrekening"),
                round(_safe_float(row.get("saldo")), 2),
                _date_str(row.get("laatste_update")),
            )
            if row_id and row_id in existing_ids:
                conn.execute(
                    "UPDATE rekeningen SET naam=?,iban=?,type=?,categorie=?,saldo=?,laatste_update=? WHERE id=?",
                    vals + (row_id,),
                )
                seen_ids.add(row_id)
            else:
                try:
                    cur = conn.execute(
                        "INSERT INTO rekeningen (naam,iban,type,categorie,saldo,laatste_update) VALUES (?,?,?,?,?,?)",
                        vals,
                    )
                    seen_ids.add(cur.lastrowid)
                except sqlite3.IntegrityError:
                    pass
        for old_id in existing_ids - seen_ids:
            conn.execute("DELETE FROM rekeningen WHERE id=?", (old_id,))
        conn.commit()


def upsert_rekening(naam: str, iban: str, type_: str = "prive",
                    categorie: str = "betaalrekening", saldo: float = 0.0) -> None:
    with get_connection() as conn:
        _init_bank_table(conn)
        exists = conn.execute(
            "SELECT id FROM rekeningen WHERE iban=?", (iban.upper(),)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO rekeningen (naam,iban,type,categorie,saldo) VALUES (?,?,?,?,?)",
                (naam, iban.upper(), type_, categorie, round(saldo, 2)),
            )
            conn.commit()


def get_bank_transactions(jaar: int, kwartaal: int = None,
                           only_unmatched: bool = False,
                           rekening: str = None) -> pd.DataFrame:
    sql = "SELECT * FROM bank_transactions WHERE jaar=?"
    params: list = [jaar]
    if kwartaal:
        sql += " AND kwartaal=?"
        params.append(kwartaal)
    if only_unmatched:
        sql += " AND expense_id IS NULL AND income_id IS NULL AND prive=0"
    if rekening:
        sql += " AND rekening=?"
        params.append(rekening)
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


def set_prive_categorie(tx_id: int, categorie: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bank_transactions SET prive_categorie=? WHERE id=?",
            (categorie.strip(), tx_id),
        )
        conn.commit()


def set_prive_categorie_by_naam(naam: str, categorie: str) -> int:
    """Apply categorie to all uncategorised transactions with the same naam. Returns count updated."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE bank_transactions SET prive_categorie=? "
            "WHERE naam=? AND (prive_categorie IS NULL OR prive_categorie='')",
            (categorie.strip(), naam),
        )
        conn.commit()
        return cur.rowcount


def get_prive_spending(jaar: int, maand: int = None, rekening: str = None) -> pd.DataFrame:
    sql = "SELECT * FROM bank_transactions WHERE jaar=? AND bedrag < 0"
    params: list = [jaar]
    if maand:
        sql += " AND CAST(strftime('%m', datum) AS INTEGER)=?"
        params.append(maand)
    if rekening:
        sql += " AND rekening=?"
        params.append(rekening)
    else:
        sql += " AND rekening IN (SELECT iban FROM rekeningen WHERE type='prive')"
    sql += " ORDER BY datum DESC, id DESC"
    with get_connection() as conn:
        _init_bank_table(conn)
        df = pd.read_sql_query(sql, conn, params=params)
    if not df.empty:
        df["datum"] = df["datum"].apply(_to_date)
    return df


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


# ── Privé: schulden, vaste lasten, inkomsten ──────────────────────────────────

FREQUENTIES = ["maandelijks", "kwartaal", "halfjaar", "jaar", "eenmalig"]


def _init_prive_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schulden (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            naam              TEXT    NOT NULL DEFAULT '',
            partij            TEXT    NOT NULL DEFAULT '',
            iban              TEXT    NOT NULL DEFAULT '',
            origineel_bedrag  REAL    NOT NULL DEFAULT 0,
            huidig_restant    REAL    NOT NULL DEFAULT 0,
            termijn_bedrag    REAL    NOT NULL DEFAULT 0,
            frequentie        TEXT    NOT NULL DEFAULT 'maandelijks',
            start_datum       TEXT    NOT NULL DEFAULT '',
            aantal_termijnen  INTEGER NOT NULL DEFAULT 0,
            betaald_termijnen INTEGER NOT NULL DEFAULT 0,
            extra_betaald     REAL    NOT NULL DEFAULT 0,
            betaaldatum       TEXT    NOT NULL DEFAULT '',
            actief            INTEGER NOT NULL DEFAULT 1,
            notities          TEXT    NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS vaste_lasten (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            naam        TEXT    NOT NULL DEFAULT '',
            partij      TEXT    NOT NULL DEFAULT '',
            iban        TEXT    NOT NULL DEFAULT '',
            bedrag      REAL    NOT NULL DEFAULT 0,
            frequentie  TEXT    NOT NULL DEFAULT 'maandelijks',
            betaaldatum TEXT    NOT NULL DEFAULT '',
            categorie   TEXT    NOT NULL DEFAULT '',
            actief      INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS prive_inkomsten (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            naam    TEXT    NOT NULL DEFAULT '',
            bedrag  REAL    NOT NULL DEFAULT 0,
            jaar    INTEGER NOT NULL,
            maand   INTEGER NOT NULL
        );
    """)
    # Migrations for tables created before this schema
    from datetime import date
    today = date.today()
    new_cols = [
        ("schulden",    "start_datum",       "TEXT    NOT NULL DEFAULT ''"),
        ("schulden",    "aantal_termijnen",  "INTEGER NOT NULL DEFAULT 0"),
        ("schulden",    "betaald_termijnen", "INTEGER NOT NULL DEFAULT 0"),
        ("schulden",    "extra_betaald",     "REAL    NOT NULL DEFAULT 0"),
        ("schulden",    "betaaldatum",       "TEXT    NOT NULL DEFAULT ''"),
        ("vaste_lasten","betaaldatum",       "TEXT    NOT NULL DEFAULT ''"),
    ]
    for table, col, defn in new_cols:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    # Convert legacy betaaldag (day-of-month integer) to betaaldatum (YYYY-MM-DD)
    for table in ("schulden", "vaste_lasten"):
        try:
            rows = conn.execute(
                f"SELECT id, betaaldag FROM {table} WHERE betaaldatum='' AND betaaldag>0"
            ).fetchall()
            for row_id, day in rows:
                # Use next occurrence of that day from today
                try:
                    dt = today.replace(day=int(day))
                except ValueError:
                    dt = today  # day > days-in-month; fallback
                if dt < today:
                    # Advance one month
                    m, y = today.month % 12 + 1, today.year + (1 if today.month == 12 else 0)
                    try:
                        dt = dt.replace(year=y, month=m)
                    except ValueError:
                        dt = today
                conn.execute(
                    f"UPDATE {table} SET betaaldatum=? WHERE id=?",
                    (dt.isoformat(), row_id),
                )
            conn.commit()
        except sqlite3.OperationalError:
            pass


def monthly_equivalent(bedrag: float, frequentie: str) -> float:
    """Return the monthly cost equivalent for any payment frequency."""
    return {
        "maandelijks": bedrag,
        "kwartaal":    bedrag / 3,
        "halfjaar":    bedrag / 6,
        "jaar":        bedrag / 12,
        "eenmalig":    0.0,
    }.get(frequentie, bedrag)


# ── Schulden ──────────────────────────────────────────────────────────────────

def get_schulden(only_actief: bool = False) -> pd.DataFrame:
    with get_connection() as conn:
        _init_prive_tables(conn)
        sql = "SELECT * FROM schulden"
        if only_actief:
            sql += " WHERE actief=1"
        sql += " ORDER BY actief DESC, naam"
        df = pd.read_sql_query(sql, conn)
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "naam", "partij", "iban", "origineel_bedrag",
            "huidig_restant", "termijn_bedrag", "frequentie",
            "start_datum", "aantal_termijnen", "betaald_termijnen", "extra_betaald",
            "betaaldatum", "actief", "notities",
        ])
    df["actief"] = df["actief"].astype(bool)
    for col in ("start_datum", "betaaldatum"):
        if col in df.columns:
            df[col] = df[col].apply(_to_date)
    return df


def save_schulden(df: pd.DataFrame) -> None:
    with get_connection() as conn:
        _init_prive_tables(conn)
        existing_ids = {r[0] for r in conn.execute("SELECT id FROM schulden").fetchall()}
        seen_ids: set[int] = set()
        for _, row in df.iterrows():
            naam = str(row.get("naam") or "").strip()
            if not naam:
                continue
            row_id = _safe_int(row.get("id"), 0)
            origineel = round(_safe_float(row.get("origineel_bedrag")), 2)
            termijn = round(_safe_float(row.get("termijn_bedrag")), 2)
            betaald = _safe_int(row.get("betaald_termijnen"), 0)
            extra = round(_safe_float(row.get("extra_betaald")), 2)
            huidig_restant = max(0.0, round(origineel - termijn * betaald - extra, 2))
            vals = (
                naam,
                str(row.get("partij") or "").strip(),
                str(row.get("iban") or "").strip(),
                origineel,
                huidig_restant,
                termijn,
                str(row.get("frequentie") or "maandelijks"),
                _date_str(row.get("start_datum")),
                _safe_int(row.get("aantal_termijnen"), 0),
                betaald,
                extra,
                _date_str(row.get("betaaldatum")),
                _safe_bool(row.get("actief")),
                str(row.get("notities") or "").strip(),
            )
            if row_id and row_id in existing_ids:
                conn.execute(
                    "UPDATE schulden SET naam=?,partij=?,iban=?,origineel_bedrag=?,"
                    "huidig_restant=?,termijn_bedrag=?,frequentie=?,"
                    "start_datum=?,aantal_termijnen=?,betaald_termijnen=?,extra_betaald=?,"
                    "betaaldatum=?,actief=?,notities=? WHERE id=?",
                    vals + (row_id,),
                )
                seen_ids.add(row_id)
            else:
                cur = conn.execute(
                    "INSERT INTO schulden (naam,partij,iban,origineel_bedrag,"
                    "huidig_restant,termijn_bedrag,frequentie,"
                    "start_datum,aantal_termijnen,betaald_termijnen,extra_betaald,"
                    "betaaldatum,actief,notities) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    vals,
                )
                seen_ids.add(cur.lastrowid)
        for old_id in existing_ids - seen_ids:
            conn.execute("DELETE FROM schulden WHERE id=?", (old_id,))
        conn.commit()


def upsert_schuld(naam: str, partij: str, origineel_bedrag: float,
                  huidig_restant: float, termijn_bedrag: float,
                  frequentie: str = "maandelijks", actief: bool = True,
                  notities: str = "") -> None:
    """Insert a schuld if naam+partij doesn't exist yet (used by importer)."""
    with get_connection() as conn:
        _init_prive_tables(conn)
        exists = conn.execute(
            "SELECT id FROM schulden WHERE naam=? AND partij=?", (naam, partij)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO schulden (naam,partij,origineel_bedrag,huidig_restant,"
                "termijn_bedrag,frequentie,actief,notities) VALUES (?,?,?,?,?,?,?,?)",
                (naam, partij, round(origineel_bedrag, 2), round(huidig_restant, 2),
                 round(termijn_bedrag, 2), frequentie, int(actief), notities),
            )
            conn.commit()


# ── Vaste lasten ──────────────────────────────────────────────────────────────

def get_vaste_lasten(only_actief: bool = False) -> pd.DataFrame:
    with get_connection() as conn:
        _init_prive_tables(conn)
        sql = "SELECT * FROM vaste_lasten"
        if only_actief:
            sql += " WHERE actief=1"
        sql += " ORDER BY actief DESC, naam"
        df = pd.read_sql_query(sql, conn)
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "naam", "partij", "iban", "bedrag",
            "frequentie", "betaaldatum", "categorie", "actief",
        ])
    df["actief"] = df["actief"].astype(bool)
    if "betaaldatum" in df.columns:
        df["betaaldatum"] = df["betaaldatum"].apply(_to_date)
    return df


def save_vaste_lasten(df: pd.DataFrame) -> None:
    with get_connection() as conn:
        _init_prive_tables(conn)
        existing_ids = {r[0] for r in conn.execute("SELECT id FROM vaste_lasten").fetchall()}
        seen_ids: set[int] = set()
        for _, row in df.iterrows():
            naam = str(row.get("naam") or "").strip()
            if not naam:
                continue
            row_id = _safe_int(row.get("id"), 0)
            vals = (
                naam,
                str(row.get("partij") or "").strip(),
                str(row.get("iban") or "").strip(),
                round(_safe_float(row.get("bedrag")), 2),
                str(row.get("frequentie") or "maandelijks"),
                _date_str(row.get("betaaldatum")),
                str(row.get("categorie") or "").strip(),
                _safe_bool(row.get("actief")),
            )
            if row_id and row_id in existing_ids:
                conn.execute(
                    "UPDATE vaste_lasten SET naam=?,partij=?,iban=?,bedrag=?,"
                    "frequentie=?,betaaldatum=?,categorie=?,actief=? WHERE id=?",
                    vals + (row_id,),
                )
                seen_ids.add(row_id)
            else:
                cur = conn.execute(
                    "INSERT INTO vaste_lasten (naam,partij,iban,bedrag,"
                    "frequentie,betaaldatum,categorie,actief) VALUES (?,?,?,?,?,?,?,?)",
                    vals,
                )
                seen_ids.add(cur.lastrowid)
        for old_id in existing_ids - seen_ids:
            conn.execute("DELETE FROM vaste_lasten WHERE id=?", (old_id,))
        conn.commit()


def upsert_vaste_last(naam: str, bedrag: float, frequentie: str = "maandelijks",
                      betaaldag: int = 1, categorie: str = "") -> None:
    """Insert a vaste last if naam doesn't exist yet (used by importer)."""
    with get_connection() as conn:
        _init_prive_tables(conn)
        exists = conn.execute(
            "SELECT id FROM vaste_lasten WHERE naam=?", (naam,)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO vaste_lasten (naam,bedrag,frequentie,betaaldag,categorie,actief) "
                "VALUES (?,?,?,?,?,1)",
                (naam, round(bedrag, 2), frequentie, betaaldag, categorie),
            )
            conn.commit()


# ── Privé inkomsten ───────────────────────────────────────────────────────────

def get_prive_inkomsten(jaar: int, maand: int = None) -> pd.DataFrame:
    sql = "SELECT * FROM prive_inkomsten WHERE jaar=?"
    params: list = [jaar]
    if maand:
        sql += " AND maand=?"
        params.append(maand)
    sql += " ORDER BY maand, naam"
    with get_connection() as conn:
        _init_prive_tables(conn)
        df = pd.read_sql_query(sql, conn, params=params)
    if df.empty:
        return pd.DataFrame(columns=["id", "naam", "bedrag", "jaar", "maand"])
    return df


def save_prive_inkomsten(df: pd.DataFrame, jaar: int, maand: int) -> None:
    with get_connection() as conn:
        _init_prive_tables(conn)
        conn.execute("DELETE FROM prive_inkomsten WHERE jaar=? AND maand=?", (jaar, maand))
        for _, row in df.iterrows():
            naam = str(row.get("naam") or "").strip()
            if not naam:
                continue
            conn.execute(
                "INSERT INTO prive_inkomsten (naam, bedrag, jaar, maand) VALUES (?,?,?,?)",
                (naam, round(_safe_float(row.get("bedrag")), 2), jaar, maand),
            )
        conn.commit()
