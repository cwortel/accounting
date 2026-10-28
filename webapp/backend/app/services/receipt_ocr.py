"""Local OCR text extraction + heuristic field parsing for scanned/photographed receipts.

Every extraction here is a best-effort guess — the review UI always lets the
user correct fields before an Expense is created, so heuristics are kept
simple rather than chasing perfect accuracy.
"""

import re
from datetime import date
from pathlib import Path

import pymupdf as fitz
import pytesseract
from PIL import Image

OCR_LANG = "nld+eng"

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

# Covers both Dutch ("mrt", "mei", "okt") and English ("mar", "may", "oct")
# month abbreviations/spellings, matched by their first 3 letters.
_MONTH_ABBR = {
    "jan": 1, "feb": 2, "mrt": 3, "mar": 3, "apr": 4, "mei": 5, "may": 5,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11, "dec": 12,
}

_MIN_TEXT_LAYER_LEN = 20


def extract_text(path: Path) -> tuple[str, str]:
    """Returns (plain_text, mime_type)."""
    suffix = path.suffix.lower()
    mime_type = MIME_TYPES.get(suffix, "application/octet-stream")

    if suffix == ".pdf":
        with fitz.open(path) as doc:
            text = "\n".join(page.get_text() for page in doc)
            if len(text.strip()) >= _MIN_TEXT_LAYER_LEN:
                return text, mime_type
            # No usable text layer (scanned PDF) — rasterize pages and OCR them.
            ocr_chunks = []
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                ocr_chunks.append(_ocr_image(img))
            return "\n".join(ocr_chunks), mime_type

    img = Image.open(path)
    return _ocr_image(img), mime_type


def _ocr_image(img: Image.Image) -> str:
    try:
        return pytesseract.image_to_string(img, lang=OCR_LANG)
    except pytesseract.TesseractError:
        return pytesseract.image_to_string(img)


# Guarded on both sides so we don't match a fragment of a longer dotted/comma'd
# number such as a VAT registration number (e.g. "237.16.367" -> false "237.16").
_AMOUNT_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})(?![\d.,])")
# Word-boundaries matter here: without them "bedrag" would also match inside an
# unrelated word like "factuurbedrag" ("invoice amount [will be collected]").
_TOTAL_KEYWORD_RE = re.compile(r"\b(totaal|te\s+betalen|eindtotaal|bedrag)\b", re.IGNORECASE)
# Prefer an explicit "te betalen"/"eindtotaal" line (the incl.-BTW amount we want
# for an expense) over a generic "totaal"/"bedrag" line labeled "exclusief" BTW.
_PAY_KEYWORD_RE = re.compile(r"te\s+betalen|eindtotaal", re.IGNORECASE)
_EXCL_BTW_RE = re.compile(r"exclusief|excl\.?\s*btw", re.IGNORECASE)
# Optional decimal part so "9.00%"/"21,00%" (not just "9%") are recognized too.
_BTW_PCT_RE = re.compile(r"\b(\d{1,2})(?:[.,]\d+)?\s*%")
_DATE_NUMERIC_RE = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b")
_DATE_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
# Day + month-name + year, separated by spaces OR dashes, e.g. "27 juli 2026",
# "18 september 2026" (Dutch) or "11-JUL-2026" (English, Adobe-style invoices).
_DATE_MONTH_NAME_RE = re.compile(r"\b(\d{1,2})[-\s]+([A-Za-z]{3,9})\.?[-\s]+(\d{4})\b")
# A Dutch postal code ("3961 CJ") on its own address line is a strong anchor: the
# company name is almost always 1-2 lines above it (above any street-address line).
_POSTCODE_LINE_RE = re.compile(r"\b\d{4}\s?[A-Z]{2}\b")
_STREET_LINE_RE = re.compile(r"\d")
# Only the vendor's own address block is followed by its KVK/BIC reference — a
# customer's address block never is, so this disambiguates the two.
_VENDOR_ID_LOOKAHEAD_RE = re.compile(r"kvk|bic", re.IGNORECASE)
_LOOKAHEAD_LINES = 4
_LEGAL_SUFFIX_RE = re.compile(r"\b(b\.?v\.?|n\.?v\.?|vof|ltd|inc|gmbh|llc)\b", re.IGNORECASE)
_WWW_DOMAIN_RE = re.compile(r"\bwww\.([a-z0-9-]+)\.(?:com|nl|net|org|eu|be)\b", re.IGNORECASE)
_EMAIL_DOMAIN_RE = re.compile(r"[\w.-]+@([a-z0-9-]+)\.(?:com|nl|net|org|eu|be)\b", re.IGNORECASE)
_TIME_ONLY_RE = re.compile(r"^\d{1,2}:\d{2}$")
_HEADER_WORDS = {
    "omschrijving", "bedrag", "totaal", "totaalbedrag", "eindtotaal", "subtotaal",
    "btw", "factuur", "factuuradres", "factuurdatum", "factuurnummer", "aantal",
    "prijs/st", "korting", "datum", "bestelnummer", "klantnummer", "vervaldatum",
    "bon", "kassabon",
}


def _parse_amount(raw: str) -> float | None:
    cleaned = raw.replace(".", "").replace(",", ".") if "," in raw else raw
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def _extract_total(lines: list[str]) -> float | None:
    candidates: list[tuple[int, list[float]]] = []
    keyword_idxs: list[int] = []
    for i, line in enumerate(lines):
        # Zero-amount line items (discounts reaching 0, free add-ons) are never the
        # invoice total, and including them lets a nearby one win a proximity tie.
        amounts = [a for a in (_parse_amount(m) for m in _AMOUNT_RE.findall(line)) if a]
        if amounts:
            candidates.append((i, amounts))
        if _TOTAL_KEYWORD_RE.search(line) and not _EXCL_BTW_RE.search(line):
            keyword_idxs.append(i)

    if keyword_idxs:
        # PDF text extraction often separates a label column from its value column,
        # so the total keyword and its amount end up a few lines apart rather than
        # on the same line. Prefer an explicit "te betalen"/"eindtotaal" line if one
        # exists (the amount we actually want), else the LAST generic total keyword
        # (subtotals are usually listed before the grand total).
        pay_idxs = [i for i in keyword_idxs if _PAY_KEYWORD_RE.search(lines[i])]
        target_idx = pay_idxs[-1] if pay_idxs else keyword_idxs[-1]
        best: float | None = None
        best_key: tuple[int, int] | None = None
        for i, amounts in candidates:
            # On a tied distance, prefer the amount AFTER the label over the one
            # before it — "label, then its value" is the dominant invoice layout
            # (e.g. "Totaal te betalen" / "€ 254,18"); a tied amount before the
            # label is more often an unrelated figure, such as the BTW line above it.
            key = (abs(i - target_idx), 0 if i > target_idx else 1)
            if best_key is None or key < best_key:
                best_key, best = key, max(amounts)
        if best is not None and best_key is not None and best_key[0] <= 5:
            return best

    all_amounts = [a for _, amounts in candidates for a in amounts]
    return max(all_amounts) if all_amounts else None


def _extract_btw_pct(text: str) -> int | None:
    # Percentages are frequently printed in their own column, separated from the
    # word "btw" by the PDF's text extraction order, so we don't require them on
    # the same line — instead count every valid-rate mention in the whole document
    # and take the dominant one. A genuine tie (e.g. a receipt mixing 9% and 21%
    # items) returns None rather than silently guessing one of them.
    counts = {0: 0, 9: 0, 21: 0}
    for m in _BTW_PCT_RE.finditer(text):
        pct = int(m.group(1))
        if pct in counts:
            counts[pct] += 1
    best_pct, best_count = max(counts.items(), key=lambda kv: kv[1])
    if best_count == 0:
        return None
    if list(counts.values()).count(best_count) > 1:
        return None
    return best_pct


def _extract_date(text: str) -> date | None:
    m = _DATE_ISO_RE.search(text)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            pass

    for m in _DATE_MONTH_NAME_RE.finditer(text):
        day, year = int(m.group(1)), int(m.group(3))
        month = _MONTH_ABBR.get(m.group(2)[:3].lower())
        if not month:
            continue
        try:
            return date(year, month, day)
        except ValueError:
            continue

    for m in _DATE_NUMERIC_RE.finditer(text):
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        if day > 31 or month > 12:
            continue
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return None


def _naam_before_postcode(lines: list[str], postcode_idx: int) -> str | None:
    idx = postcode_idx - 1
    if idx >= 0 and _STREET_LINE_RE.search(lines[idx]):
        idx -= 1
    if idx >= 0:
        candidate = lines[idx].strip()
        if len(candidate) >= 2 and candidate.lower() not in _HEADER_WORDS:
            return candidate
    return None


def _naam_from_postcode_block(lines: list[str]) -> str | None:
    # An invoice usually prints both the customer's and the vendor's address —
    # only treat a postcode line as the vendor's if a KVK/BIC reference follows
    # shortly after it, which a customer's address block never has.
    for i, line in enumerate(lines):
        if not _POSTCODE_LINE_RE.search(line):
            continue
        window = lines[i + 1 : i + 1 + _LOOKAHEAD_LINES]
        if any(_VENDOR_ID_LOOKAHEAD_RE.search(w) for w in window):
            candidate = _naam_before_postcode(lines, i)
            if candidate:
                return candidate
    return None


def _naam_from_domain(lines: list[str]) -> str | None:
    for line in lines:
        m = _WWW_DOMAIN_RE.search(line) or _EMAIL_DOMAIN_RE.search(line)
        if m:
            return m.group(1).replace("-", " ").replace(".", " ").strip().title()
    return None


def _extract_naam(lines: list[str]) -> str:
    # Strongest signal: a Dutch/international legal-entity suffix (B.V., Ltd, ...)
    # almost always marks the actual company name, wherever it appears in the text.
    for line in lines:
        stripped = line.strip()
        if len(stripped) <= 80 and _LEGAL_SUFFIX_RE.search(stripped):
            return stripped

    candidate = _naam_from_postcode_block(lines)
    if candidate:
        return candidate

    candidate = _naam_from_domain(lines)
    if candidate:
        return candidate

    # Last resort: first substantial line that isn't a generic invoice/receipt header
    # word or a bare date (dates are easily mis-picked when nothing else matches).
    for line in lines:
        stripped = line.strip()
        if (
            len(stripped) >= 2
            and not stripped.isdigit()
            and stripped.lower() not in _HEADER_WORDS
            and not _DATE_MONTH_NAME_RE.fullmatch(stripped)
            and not _DATE_NUMERIC_RE.fullmatch(stripped)
            and not _DATE_ISO_RE.fullmatch(stripped)
            and not _TIME_ONLY_RE.fullmatch(stripped)
        ):
            return stripped
    return ""


def parse_fields(text: str) -> dict:
    lines = [line for line in text.splitlines() if line.strip()]
    return {
        "naam": _extract_naam(lines),
        "datum": _extract_date(text),
        "total": _extract_total(lines),
        "btw_pct": _extract_btw_pct(text),
    }
