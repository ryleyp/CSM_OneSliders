"""screenshot_reader.py

Local OCR (pytesseract / Pillow) for the three contract screenshots, plus
tolerant per-screenshot text parsers.

These screenshots are messy two-column tables, so the parsers are deliberately
forgiving: they SEARCH the OCR text for known signals rather than assuming
clean key/value rows. Every value produced here is a *suggestion* — app.py
drops each one into an editable field that the user must review and correct
before generating. OCR is imperfect; that review step is mandatory.

No network calls. Tesseract is a system binary the user installs separately;
if it is missing we surface a clear message instead of crashing.
"""

from __future__ import annotations

import re

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    _OCR_AVAILABLE = False


# --------------------------------------------------------------------------- #
# OCR entry point
# --------------------------------------------------------------------------- #
def ocr_image(image_file) -> str:
    """Run Tesseract on an uploaded image and return raw text.

    `image_file` is anything PIL can open (a path or a Streamlit UploadedFile).
    Returns '' and never raises on a missing/broken Tesseract install.
    """
    if not _OCR_AVAILABLE:
        return ""
    try:
        img = Image.open(image_file)
        # Grayscale tends to help Tesseract on screenshots.
        if img.mode != "L":
            img = img.convert("L")
        return pytesseract.image_to_string(img)
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract OCR is not installed on this machine. Install the system "
            "Tesseract package (see README) and try again."
        )
    except Exception:
        return ""


def _clean(line: str) -> str:
    return re.sub(r"\s+", " ", line or "").strip()


# --------------------------------------------------------------------------- #
# Screenshot A - Contract details
# --------------------------------------------------------------------------- #
def parse_contract_details(text: str) -> dict:
    """Search messy two-column OCR text for the specific contract fields.

    Returns a dict of best-guess values (any of which may be ''):
      service_id, customer, start_date, ep_term, flex_credits,
      support_level, debug_licenses
    """
    text = text or ""
    lines = [l for l in (text.splitlines()) if l.strip()]
    flat = " ".join(lines)
    result = {
        "service_id": "",
        "customer": "",
        "start_date": "",
        "ep_term": "",
        "flex_credits": "",
        "support_level": "",
        "debug_licenses": "",
    }

    # EA/EP Service ID -> "EA-#####"
    m = re.search(r"\bEA[-\s]?(\d{4,6})\b", flat, re.IGNORECASE)
    if m:
        result["service_id"] = f"EA-{m.group(1)}"

    # Company / customer name: first line of the Company cell. Find a line that
    # mentions "Company" / "Customer" and take the trailing text, or the next
    # non-empty line if the label sits on its own.
    for i, line in enumerate(lines):
        if re.search(r"\b(company|customer)\b", line, re.IGNORECASE):
            # Strip the label + any footnote superscript digits off the front.
            tail = re.sub(r"(?i).*\b(company|customer)\b[^A-Za-z0-9]*\d*\s*", "",
                          _clean(line)).strip()
            if len(tail) >= 2:
                result["customer"] = tail.split("  ")[0].strip()
            elif i + 1 < len(lines):
                result["customer"] = _clean(lines[i + 1])
            break

    # Start / Effective date, e.g. "02-JAN-2026".
    m = re.search(r"\b(\d{1,2}[-/\s][A-Za-z]{3,9}[-/\s]\d{2,4}"
                  r"|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
                  r"|\d{4}-\d{2}-\d{2})\b", flat)
    # Prefer a date that sits on a line mentioning start/effective.
    for line in lines:
        if re.search(r"\b(start|effective)\b", line, re.IGNORECASE):
            dm = re.search(r"\b(\d{1,2}[-/\s][A-Za-z]{3,9}[-/\s]\d{2,4}"
                           r"|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
                           r"|\d{4}-\d{2}-\d{2})\b", line)
            if dm:
                m = dm
                break
    if m:
        result["start_date"] = m.group(1)

    # EP Term, e.g. "3 years" / "36 months".
    m = re.search(r"(\d+)\s*(year|yr|month|mo)s?\b", flat, re.IGNORECASE)
    if m:
        unit = "years" if m.group(2).lower().startswith(("year", "yr")) else "months"
        result["ep_term"] = f"{m.group(1)} {unit}"

    # EA FLEX Credits, e.g. "EA FLEX Credits 20,000".
    m = re.search(r"FLEX\s*Credits?\D*([\d,]{2,})", flat, re.IGNORECASE)
    if m:
        result["flex_credits"] = m.group(1).strip()

    # Support level / Services info: capture the trailing text of a Support line.
    # Skip the Service ID line and any FLEX line so we don't grab those values.
    for line in lines:
        low = line.lower()
        if "service id" in low or "flex" in low:
            continue
        m = re.search(r"\b(?:support(?:\s+level)?|services?\s+(?:level|info))"
                      r"\s*[:\-]?\s+(.+)$", _clean(line), re.IGNORECASE)
        if m:
            tail = m.group(1).strip()
            if 2 <= len(tail) <= 60:
                result["support_level"] = tail
                break

    # Debug licenses included (Yes/No).
    m = re.search(r"debug[^\n]*?\b(yes|no|included|y|n)\b", flat, re.IGNORECASE)
    if m:
        val = m.group(1).lower()
        result["debug_licenses"] = "Yes" if val in ("yes", "included", "y") else "No"

    return result


# --------------------------------------------------------------------------- #
# Screenshot B - Finite licenses
# --------------------------------------------------------------------------- #
def parse_finite_licenses(text: str) -> list[dict]:
    """Parse the 'Quantity and License Type' / 'Software Title' table.

    Each data row: split the leading NUMBER off as the count, the rest of that
    first cell as the license type, and the second column as the license name.
    The header row 'Finite Quantity NI Software Licenses' is ignored.

    Returns a list of {count, license_type, license_name}.
    """
    rows: list[dict] = []
    for raw in (text or "").splitlines():
        line = _clean(raw)
        if not line:
            continue
        if re.search(r"finite\s+quantity", line, re.IGNORECASE):
            continue  # header
        if re.search(r"quantity\s+and\s+license", line, re.IGNORECASE):
            continue  # column header

        # A row must start with a leading count number.
        m = re.match(r"^(\d[\d,]*)\s+(.*)$", line)
        if not m:
            continue
        count = int(m.group(1).replace(",", ""))
        rest = m.group(2)

        # Split license TYPE from license NAME. Prefer a tab; otherwise use a
        # 2+ space gap; otherwise fall back on known type keywords.
        license_type, license_name = _split_type_and_name(rest, raw)
        rows.append(
            {"count": count, "license_type": license_type,
             "license_name": license_name}
        )
    return rows


_TYPE_KEYWORDS = (
    "named user or computer based", "named-user or computer-based",
    "named user", "named-user", "computer based", "computer-based",
    "concurrent", "floating", "node locked", "node-locked", "site",
)


def _split_type_and_name(rest: str, raw: str) -> tuple[str, str]:
    """Separate the license type from the software title within a row."""
    # If the original line had a tab, the cells are clean.
    if "\t" in raw:
        parts = [p.strip() for p in raw.split("\t") if p.strip()]
        # parts[0] is "<count> <type>" already consumed; rebuild from raw tabs.
        if len(parts) >= 2:
            first = re.sub(r"^\d[\d,]*\s*", "", parts[0]).strip()
            return first, parts[1].strip()

    # Wide-space split.
    chunks = re.split(r"\s{2,}", rest)
    if len(chunks) >= 2:
        return chunks[0].strip(), " ".join(c.strip() for c in chunks[1:]).strip()

    # Keyword-based split: the type is a known phrase at the start.
    low = rest.lower()
    for kw in _TYPE_KEYWORDS:
        if low.startswith(kw):
            return rest[:len(kw)].strip(), rest[len(kw):].strip()

    # Could not separate; treat the whole thing as the type.
    return rest.strip(), ""


# --------------------------------------------------------------------------- #
# Screenshot C - Unlimited bundles
# --------------------------------------------------------------------------- #
def parse_unlimited_bundles(text: str) -> list[str]:
    """Extract bundle names from the 'Unlimited Quantity NI Software Licenses'
    table.

    The title column reads e.g. 'EP Bundle Title: EA Platform Bundle'. We keep
    just the bundle name AFTER the colon. The header row is ignored.
    """
    bundles: list[str] = []
    for raw in (text or "").splitlines():
        line = _clean(raw)
        if not line:
            continue
        if re.search(r"unlimited\s+quantity", line, re.IGNORECASE):
            continue  # header

        # Bundle name follows a label + colon, e.g. "... Bundle Title: <name>".
        m = re.search(r"(?:bundle\s*title|title)\s*[:\-]\s*(.+)$", line,
                      re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if name:
                bundles.append(name)
            continue

        # Fallback: any line containing a colon where the right side looks like
        # a bundle name (and the left side mentions 'bundle').
        if ":" in line and re.search(r"bundle", line, re.IGNORECASE):
            name = line.split(":", 1)[1].strip()
            if name and not re.search(r"unlimited\s+quantity", name, re.IGNORECASE):
                bundles.append(name)

    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for b in bundles:
        if b.lower() not in seen:
            seen.add(b.lower())
            unique.append(b)
    return unique
