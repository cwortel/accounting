"""One-off backfill: populate bank_ref (CAMT NtryRef) on existing bank_transactions
rows that were imported before bank_ref existed, by re-parsing the original XML files
in data/BankTransactions/ and matching rows on (bestand, datum, bedrag, iban).

Needed for airtight de-duplication: without this, rows imported before the bank_ref
column existed have no stable reference to match against, so a re-export of the same
transaction with a tiny formatting difference (e.g. rounding) could slip past the
composite-key fallback and be imported as a duplicate.

Usage (run from webapp/backend/):
    python -m scripts.backfill_bank_ref
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import BankTransaction


def backfill_file(db, file_path: Path) -> int:
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns_uri = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    ns = {"c": ns_uri} if ns_uri else {}

    def find(el, path):
        return el.findtext(f"c:{path}" if ns else path, namespaces=ns or None)

    filename = file_path.name
    updated = 0

    rows_by_key: dict[str, list[BankTransaction]] = {}
    for row in db.execute(select(BankTransaction).where(BankTransaction.bestand == filename)).scalars():
        rows_by_key.setdefault(f"{row.datum}_{row.bedrag}_{row.iban}", []).append(row)

    stmts = root.findall(".//c:Stmt", ns) if ns else root.findall(".//Stmt")
    for stmt in stmts:
        for entry in (stmt.findall("c:Ntry", ns) if ns else stmt.findall("Ntry")):
            ntry_ref = find(entry, "NtryRef") or ""
            if not ntry_ref:
                continue
            amt_raw = find(entry, "Amt") or "0"
            ind = find(entry, "CdtDbtInd") or "DBIT"
            bedrag = float(amt_raw) * (1 if ind == "CRDT" else -1)
            date_el = entry.find("c:BookgDt", ns) if ns else entry.find("BookgDt")
            datum = (find(date_el, "Dt") if date_el is not None else None) or ""
            detail = entry.find(".//c:TxDtls", ns) if ns else entry.find(".//TxDtls")
            src = detail if detail is not None else entry
            iban = (
                src.findtext(".//c:RltdPties/c:DbtrAcct/c:Id/c:IBAN", namespaces=ns)
                or src.findtext(".//c:RltdPties/c:CdtrAcct/c:Id/c:IBAN", namespaces=ns)
                or ""
            )
            key = f"{datum}_{bedrag}_{iban}"
            for row in rows_by_key.get(key, []):
                if not row.bank_ref:
                    row.bank_ref = ntry_ref
                    updated += 1
    return updated


def main() -> None:
    bank_dir = get_settings().bank_transactions_dir
    with SessionLocal() as db:
        total = 0
        for path in sorted(bank_dir.glob("*.xml")):
            n = backfill_file(db, path)
            print(f"{path.name}: backfilled {n} rows")
            total += n
        db.commit()
        print(f"Total backfilled: {total}")


if __name__ == "__main__":
    main()
