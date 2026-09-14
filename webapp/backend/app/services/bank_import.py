"""CAMT.053 XML and Rabobank CSV import, ported from the legacy db.py importers."""

import csv as _csv
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models


def import_camt(db: Session, file_path: str) -> int:
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns_uri = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    ns = {"c": ns_uri} if ns_uri else {}

    def find(el, path):
        return el.findtext(f"c:{path}" if ns else path, namespaces=ns or None)

    filename = Path(file_path).name
    count = 0

    # Deduplicate against ALL previously imported transactions, not just this file —
    # bank exports commonly overlap in date range with earlier exports. Prefer the
    # bank's own stable NtryRef (authoritative, survives reformatting between exports);
    # fall back to the composite key for rows imported before bank_ref existed.
    existing_by_ref: dict[tuple[str, str], models.BankTransaction] = {}
    existing_by_composite: dict[str, models.BankTransaction] = {}
    for row in db.execute(select(models.BankTransaction)).scalars():
        if row.bank_ref:
            existing_by_ref[(row.rekening, row.bank_ref)] = row
        existing_by_composite[f"{row.datum}_{row.bedrag}_{row.iban}"] = row

    latest_clbd: dict[str, float] = {}
    stmts = root.findall(".//c:Stmt", ns) if ns else root.findall(".//Stmt")
    for stmt in stmts:
        stmt_iban = (
            stmt.findtext(".//c:Acct/c:Id/c:IBAN", namespaces=ns)
            or stmt.findtext(".//Acct/Id/IBAN")
            or ""
        )

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
            ntry_ref = find(entry, "NtryRef") or ""
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

            if ntry_ref and (stmt_iban, ntry_ref) in existing_by_ref:
                continue
            composite_key = f"{datum}_{bedrag}_{iban}"
            if composite_key in existing_by_composite:
                continue

            try:
                d = pd.to_datetime(datum)
                jaar, kwartaal = d.year, (d.month - 1) // 3 + 1
            except (ValueError, TypeError):
                continue

            new_tx = models.BankTransaction(
                datum=str(datum)[:10],
                bedrag=bedrag,
                naam=naam,
                iban=iban,
                referentie=referentie,
                bestand=filename,
                jaar=jaar,
                kwartaal=kwartaal,
                rekening=stmt_iban,
                code=tx_code,
                bank_ref=ntry_ref,
            )
            db.add(new_tx)
            if ntry_ref:
                existing_by_ref[(stmt_iban, ntry_ref)] = new_tx
            existing_by_composite[composite_key] = new_tx
            count += 1

    for iban_key, saldo in latest_clbd.items():
        rekening = db.execute(
            select(models.Rekening).where(models.Rekening.iban == iban_key)
        ).scalar_one_or_none()
        if rekening:
            rekening.saldo = saldo
            rekening.laatste_update = pd.Timestamp.today().date().isoformat()

    db.commit()
    return count


def import_rabobank_csv(db: Session, file_path: str) -> int:
    filename = Path(file_path).name
    count = 0

    # Deduplicate against ALL previously imported transactions for the same account —
    # Rabobank CSV exports commonly overlap in date range with earlier exports, and
    # Volgnr is a stable identifier per account regardless of which file it came from.
    # Composite key is a defensive fallback for the rare row missing a Volgnr.
    existing_by_volgnr: dict[tuple[str, str], models.BankTransaction] = {}
    existing_by_composite: dict[tuple[str, str, float, str], models.BankTransaction] = {}
    for row in db.execute(select(models.BankTransaction)).scalars():
        if row.referentie:
            existing_by_volgnr[(row.rekening, row.referentie)] = row
        existing_by_composite[(row.rekening, row.datum, row.bedrag, row.naam)] = row

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
            naam = row["Naam tegenpartij"].strip() or row["Naam uiteindelijke partij"].strip()
            iban = row["Tegenrekening IBAN/BBAN"].strip()
            volgnr = row["Volgnr"].strip()
            tx_code = row.get("Code", "").strip()
            machtiging = row.get("Machtigingskenmerk", "").strip()
            incassant = row.get("Incassant ID", "").strip()
            referentie = " ".join(
                filter(
                    None,
                    [
                        row.get("Omschrijving-1", "").strip(),
                        row.get("Omschrijving-2", "").strip(),
                        row.get("Omschrijving-3", "").strip(),
                        row.get("Betalingskenmerk", "").strip(),
                    ],
                )
            ).strip()

            saldo_str = row.get("Saldo na trn", "").strip()
            saldo_na_trn = None
            if saldo_str:
                try:
                    saldo_na_trn = float(saldo_str.replace("+", "").replace(".", "").replace(",", "."))
                except ValueError:
                    pass

            try:
                d = pd.to_datetime(datum)
                jaar, kwartaal = d.year, (d.month - 1) // 3 + 1
            except (ValueError, TypeError):
                continue
            datum_iso = str(d.date())

            existing_tx = existing_by_volgnr.get((eigen_iban, volgnr)) if volgnr else None
            if existing_tx is None and not volgnr:
                existing_tx = existing_by_composite.get((eigen_iban, datum_iso, bedrag, naam))
            if existing_tx is not None:
                if existing_tx.saldo_na_trn is None and saldo_na_trn is not None:
                    existing_tx.saldo_na_trn = saldo_na_trn
                    existing_tx.code = tx_code
                    existing_tx.machtigingskenmerk = machtiging
                    existing_tx.incassant_id = incassant
                continue

            new_tx = models.BankTransaction(
                datum=datum_iso,
                bedrag=bedrag,
                naam=naam,
                iban=iban,
                referentie=volgnr or referentie,
                bestand=filename,
                jaar=jaar,
                kwartaal=kwartaal,
                rekening=eigen_iban,
                saldo_na_trn=saldo_na_trn,
                code=tx_code,
                machtigingskenmerk=machtiging,
                incassant_id=incassant,
            )
            db.add(new_tx)
            if volgnr:
                existing_by_volgnr[(eigen_iban, volgnr)] = new_tx
            else:
                existing_by_composite[(eigen_iban, datum_iso, bedrag, naam)] = new_tx
            count += 1

    db.flush()

    # Update rekening saldo with the most recent balance seen for accounts in this file
    touched_ibans = {
        row.rekening
        for row in db.execute(
            select(models.BankTransaction).where(models.BankTransaction.bestand == filename)
        ).scalars()
    }
    for iban_key in touched_ibans:
        latest = db.execute(
            select(models.BankTransaction)
            .where(
                models.BankTransaction.rekening == iban_key,
                models.BankTransaction.saldo_na_trn.is_not(None),
            )
            .order_by(models.BankTransaction.datum.desc(), models.BankTransaction.id.desc())
        ).scalars().first()
        if latest is None:
            continue
        rekening = db.execute(
            select(models.Rekening).where(models.Rekening.iban == iban_key)
        ).scalar_one_or_none()
        if rekening:
            rekening.saldo = latest.saldo_na_trn
            rekening.laatste_update = pd.Timestamp.today().date().isoformat()

    db.commit()
    return count
