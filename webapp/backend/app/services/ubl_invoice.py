"""Parses UBL 2.1 e-invoice XML (e.g. NLCIUS/Peppol BIS Billing 3.0), produced by
some receipt-scanning apps as a structured sidecar file next to the receipt's
PDF/image. When present, this is exact structured data — used in preference to
the OCR heuristics in receipt_ocr.py, which remain the fallback when there's no
matching XML.
"""

import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

_UBL_INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
_NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


def parse_ubl_invoice(path: Path) -> dict | None:
    """Returns the same {naam, datum, total, btw_pct} shape as receipt_ocr.parse_fields,
    or None if the file isn't a recognizable UBL invoice."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    if root.tag != f"{{{_UBL_INVOICE_NS}}}Invoice":
        return None

    naam = root.findtext("cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name", namespaces=_NS)

    datum = None
    issue_date = root.findtext("cbc:IssueDate", namespaces=_NS)
    if issue_date:
        try:
            datum = date.fromisoformat(issue_date[:10])
        except ValueError:
            datum = None

    total = None
    monetary_total = root.find("cac:LegalMonetaryTotal", _NS)
    if monetary_total is not None:
        raw_total = monetary_total.findtext("cbc:PayableAmount", namespaces=_NS) or monetary_total.findtext(
            "cbc:TaxInclusiveAmount", namespaces=_NS
        )
        if raw_total:
            try:
                total = round(float(raw_total), 2)
            except ValueError:
                total = None

    # A receipt covering a single VAT rate has one TaxCategory percent; if a
    # receipt genuinely mixes rates, don't guess which one applies to the total.
    percent_texts = [el.text for el in root.findall(".//cac:TaxCategory/cbc:Percent", _NS) if el.text]
    percents = {int(round(float(p))) for p in percent_texts}
    btw_pct = percents.pop() if len(percents) == 1 else None

    if naam is None and total is None and datum is None:
        return None

    return {
        "naam": (naam or "").strip(),
        "datum": datum,
        "total": total,
        "btw_pct": btw_pct,
    }
