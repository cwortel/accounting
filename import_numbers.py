"""One-time migration from a Numbers bookkeeping file into boekhouding.db.

Usage:
    python3 import_numbers.py /path/to/BTW2026.numbers
"""

import sys
from pathlib import Path

import numbers_parser

# Add project root to path so db.py is importable
sys.path.insert(0, str(Path(__file__).parent))
from db import init_db, get_connection  # noqa: E402


def _cell(table, row: int, col: int):
    try:
        return table.cell(row, col).value
    except Exception:
        return None


def _normalize_btw(val) -> int:
    """Convert BTW% to integer 0, 9, or 21."""
    if val is None:
        return 0
    try:
        v = float(val)
    except (TypeError, ValueError):
        return 0
    if v <= 0:
        return 0
    # stored as decimal (0.21) or as percent (21.0)
    return round(v * 100) if v <= 1 else round(v)


def _factuur_str(val) -> str:
    try:
        return str(int(float(str(val))))
    except (TypeError, ValueError):
        return str(val or "")


def _date_str(val) -> str:
    if val is None:
        return ""
    return str(val)[:10]


def import_expenses(doc, jaar: int) -> int:
    count = 0
    with get_connection() as conn:
        for q in range(1, 5):
            try:
                sheet = next(s for s in doc.sheets if s.name == f"Uitgaven Q{q}")
                table = next(t for t in sheet.tables if t.name == "Uitgaven")
            except StopIteration:
                print(f"  Q{q}: sheet or table not found, skipping.")
                continue

            headers = [str(_cell(table, 0, c) or "").strip() for c in range(table.num_cols)]
            col = {h: i for i, h in enumerate(headers)}

            q_count = 0
            for r in range(1, table.num_rows):
                naam = _cell(table, r, col.get("Naam", 1))
                if not naam or str(naam).strip() in ("", "None"):
                    continue
                factuur = _cell(table, r, col.get("Factuur", 0))
                if not factuur or str(factuur).strip() in ("", "None"):
                    continue

                afgerekend = 0
                if "Afgerekend" in col:
                    v = _cell(table, r, col["Afgerekend"])
                    afgerekend = 0 if (v is None or str(v) in ("None", "0", "0.0", "", "False")) else 1

                conn.execute(
                    "INSERT INTO expenses "
                    "(factuur,naam,datum,categorie,btw_pct,btw,ex_btw,total,afgerekend,jaar,kwartaal) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        _factuur_str(factuur),
                        str(naam),
                        _date_str(_cell(table, r, col.get("Datum", 2))),
                        str(_cell(table, r, col.get("Categorie", 3)) or "Other"),
                        _normalize_btw(_cell(table, r, col.get("BTW %", 4))),
                        round(float(_cell(table, r, col.get("BTW", 5)) or 0), 2),
                        round(float(_cell(table, r, col.get("Ex BTW", 6)) or 0), 2),
                        round(float(_cell(table, r, col.get("Total", 7)) or 0), 2),
                        afgerekend,
                        jaar,
                        q,
                    ),
                )
                q_count += 1

            print(f"  Uitgaven Q{q}: {q_count} rijen")
            count += q_count

        conn.commit()
    return count


def import_income(doc, jaar: int) -> int:
    count = 0
    with get_connection() as conn:
        for q in range(1, 5):
            try:
                sheet = next(s for s in doc.sheets if s.name == f"Inkomsten Q{q}")
                # income table is named "Table 1" across all quarters
                table = next(t for t in sheet.tables if "Table" in t.name)
            except StopIteration:
                print(f"  Q{q}: sheet or table not found, skipping.")
                continue

            headers = [str(_cell(table, 0, c) or "").strip() for c in range(table.num_cols)]
            col = {h: i for i, h in enumerate(headers)}

            # Handle naming variations across quarters
            total_col = col.get("Total", col.get("Totaal", 7))
            ex_btw_col = col.get("Ex BTW", col.get("EX BTW", 6))

            q_count = 0
            for r in range(1, table.num_rows):
                naam = _cell(table, r, col.get("Naam", 1))
                if not naam or str(naam).strip() in ("", "None"):
                    continue
                factuur = _cell(table, r, col.get("Factuur", 0))
                if not factuur or str(factuur).strip() in ("", "None"):
                    continue

                conn.execute(
                    "INSERT INTO income "
                    "(factuur,naam,datum,project,btw_pct,btw,ex_btw,total,betaald,jaar,kwartaal) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        _factuur_str(factuur),
                        str(naam),
                        _date_str(_cell(table, r, col.get("Datum", 2))),
                        str(_cell(table, r, col.get("Project", 3)) or ""),
                        _normalize_btw(_cell(table, r, col.get("BTW %", 4))),
                        round(float(_cell(table, r, col.get("BTW", 5)) or 0), 2),
                        round(float(_cell(table, r, ex_btw_col) or 0), 2),
                        round(float(_cell(table, r, total_col) or 0), 2),
                        0,  # betaald: unknown, set manually later
                        jaar,
                        q,
                    ),
                )
                q_count += 1

            print(f"  Inkomsten Q{q}: {q_count} rijen")
            count += q_count

        conn.commit()
    return count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Gebruik: python3 import_numbers.py /pad/naar/BTW2026.numbers")
        print("Voorbeeld: python3 import_numbers.py ~/Documents/BTW2026.numbers")
        sys.exit(1)

    NUMBERS_FILE = Path(sys.argv[1]).expanduser().resolve()
    if not NUMBERS_FILE.exists():
        print(f"Bestand niet gevonden: {NUMBERS_FILE}")
        sys.exit(1)

    # Derive fiscal year from filename (e.g. BTW2026.numbers → 2026)
    try:
        JAAR = int("".join(filter(str.isdigit, NUMBERS_FILE.stem)))
    except ValueError:
        JAAR = 2026
        print(f"Kan jaar niet afleiden uit bestandsnaam, gebruik {JAAR}.")

    init_db()

    with get_connection() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]

    if existing > 0:
        print(f"Let op: de database bevat al {existing} uitgaven.")
        answer = input("Overschrijven? Alle bestaande data wordt verwijderd. [j/N]: ")
        if answer.strip().lower() != "j":
            print("Geannuleerd.")
            sys.exit(0)
        with get_connection() as conn:
            conn.execute("DELETE FROM expenses")
            conn.execute("DELETE FROM income")
            conn.commit()

    print(f"\nInlezen: {NUMBERS_FILE}\n")
    doc = numbers_parser.Document(str(NUMBERS_FILE))

    print("Uitgaven:")
    exp = import_expenses(doc, JAAR)

    print("\nInkomsten:")
    inc = import_income(doc, JAAR)

    print(f"\nKlaar. {exp} uitgaven en {inc} inkomsten geïmporteerd.")
