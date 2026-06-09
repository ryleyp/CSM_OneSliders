"""
Loads contract info from a PDF using pdfplumber (with pdftotext subprocess fallback).
Regex patterns tuned to NI/Emerson Enterprise Program Amendment PDFs.
No network calls.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# PDF text extraction  (pdfplumber primary, pdftotext fallback)
# ---------------------------------------------------------------------------

def _extract_pdf_text(path: Path) -> str:
    """
    Return full text of the PDF.
    Tries pdftotext (poppler) first -- fast and reliable on both Mac and Linux.
    Falls back to pdfplumber if pdftotext is not installed.
    """
    # Primary: pdftotext (brew install poppler  /  apt install poppler-utils)
    try:
        result = subprocess.run(
            ["pdftotext", str(path), "-"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except FileNotFoundError:
        pass  # pdftotext not installed -- try pdfplumber

    # Fallback: pdfplumber (pure-Python, part of requirements.txt)
    # Import inside function so a broken cryptography lib doesn't crash the server
    try:
        import importlib
        pdfplumber = importlib.import_module("pdfplumber")
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        if text.strip():
            return text
    except Exception:
        pass

    raise RuntimeError(
        f"Could not extract text from {path.name}. "
        "Run: brew install poppler   (or: apt install poppler-utils)"
    )


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def _find(pattern: str, text: str, group: int = 1, flags: int = re.IGNORECASE) -> str:
    m = re.search(pattern, text, flags)
    return m.group(group).strip().rstrip(".,;") if m else ""


def _parse_scalar_fields(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}

    # EA Number
    ea = _find(r'\bEA[- ]?(\d{4,9})\b', text)
    if ea:
        result["ea_number"] = "EA-" + ea

    # Customer name — match “RTX Corporation (“Company”)” on its own line.
    # PDFs may use straight (“) or curly (“”) quotes.
    _anyq = '["\u201c\u201d]'  # straight and curly double quotes
    customer = _find(
        r'^([^\n(]{3,60}?)\s*\(' + _anyq + r'Company' + _anyq + r'\)\s*$',
        text, flags=re.IGNORECASE | re.MULTILINE,
    )
    if not customer:
        # Broader: “Corporation (“Company”,” — trailing comma variant
        customer = _find(
            r'^([^\n(]{3,60}?)\s*\(' + _anyq + r'Company' + _anyq,
            text, flags=re.IGNORECASE | re.MULTILINE,
        )
    if customer:
        customer = re.split(r'\s+now\s+known', customer, flags=re.IGNORECASE)[0].strip()
        result["customer_name"] = customer

    # EA end date  — "expires on January 1, 2029"
    end = _find(r'expires?\s+on\s+([\w]+ \d{1,2},?\s*\d{4})', text)
    if end:
        result["ea_end_date"] = _normalise_date(end)

    # Start date as fallback for end date
    if not result.get("ea_end_date"):
        start = _find(r'Start Date[/\w]*\s*\n\s*(\d{2}-\w+-\d{4})', text, flags=re.IGNORECASE | re.MULTILINE)
        if start:
            result["ea_start_date"] = start

    # Term — "EP Term1 3 years"  or  "three (3) years and expires"
    term = _find(r'EP Term\d*\s+(\d+)\s+years?', text)
    if not term:
        term = _find(r'for\s+(\d+)\s+\(\d+\)\s+years?', text)
    if not term:
        # "three (3) years"
        m = re.search(r'(one|two|three|four|five)\s+\(\d+\)\s+years?', text, re.IGNORECASE)
        if m:
            word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
            term = str(word_to_num.get(m.group(1).lower(), m.group(1)))
    if term:
        result["term_duration"] = f"{term} Year{'s' if term != '1' else ''}"

    # EA FLEX Credits total — "EA FLEX Credits6 20,000 for EP Term"
    flex = _find(r'EA FLEX Credits\d*\s+([\d,]+)', text)
    if flex:
        result["training_credits_total"] = int(flex.replace(",", ""))

    # Support level — "support access level is Enterprise Support"
    support = _find(r"support access level (?:is |set forth below\s+)?([A-Za-z ]+?)(?:\.|$|\n)", text)
    if support:
        result["technical_support_level"] = support.strip()

    # Scope / Phase are rarely explicit in NI EPs; leave for manual entry
    result.setdefault("contract_scope", "Enterprise Program")

    return result


def _normalise_date(raw: str) -> str:
    """Convert 'January 1, 2029' or '02-JAN-2026' to YYYY-MM-DD."""
    import calendar
    # Already ISO
    if re.match(r'\d{4}-\d{2}-\d{2}', raw):
        return raw
    # DD-MON-YYYY
    m = re.match(r'(\d{2})-([A-Za-z]{3})-(\d{4})', raw)
    if m:
        months = {v: k for k, v in enumerate(calendar.month_abbr) if v}
        mo = months.get(m.group(2).capitalize(), 0)
        return f"{m.group(3)}-{mo:02d}-{int(m.group(1)):02d}"
    # Month DD, YYYY
    m = re.match(r'([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})', raw)
    if m:
        months = {v.lower(): k for k, v in enumerate(calendar.month_name) if v}
        mo = months.get(m.group(1).lower(), 0)
        return f"{m.group(3)}-{mo:02d}-{int(m.group(2)):02d}"
    return raw


# ---------------------------------------------------------------------------
# License and bundle table extraction
# ---------------------------------------------------------------------------

def _parse_licenses(text: str) -> list[dict]:
    """
    Extract finite quantity licenses from NI EP Amendment PDFs.

    The text layout after pdftotext/pdfplumber looks like:
        Software Title Name
        142 Named User or Computer Based
        Another Product
        23 Concurrent
    i.e. product name on one line, quantity + type on the next.
    """
    licenses: list[dict] = []

    # Find the finite quantity section
    m = re.search(
        r'Finite Quantity NI Software Licenses\s*\n(.+?)(?=All Finite Quantity|Unlimited Quantity)',
        text, re.DOTALL | re.IGNORECASE,
    )
    if not m:
        # Broader fallback: look for the schedule table in Attachment D
        m = re.search(
            r'Schedule A.*?Software Title\s+License Type\s+Seat Included.*?\n(.+?)(?=NI Confidential|\Z)',
            text, re.DOTALL | re.IGNORECASE,
        )

    if m:
        block = m.group(1)
        lines = [l.strip() for l in block.splitlines() if l.strip()]

        # Skip header noise lines
        noise = {"quantity and license type", "software title", "license type",
                 "seat included", "cost of additional"}

        i = 0
        while i < len(lines) - 1:
            current = lines[i]
            nxt     = lines[i + 1]

            if current.lower() in noise or nxt.lower() in noise:
                i += 1
                continue

            # Match: next line is "NUMBER TYPE"
            qty_match = re.match(r'^(\d+)\s+(.+)$', nxt)
            if qty_match:
                qty      = int(qty_match.group(1))
                lic_type = qty_match.group(2).strip()
                name     = current

                # Sanity-check: name should look like a product (not a sentence)
                if len(name) < 60 and not re.search(r'[\$]', name):
                    licenses.append({
                        "count": qty,
                        "name":  name,
                        "type":  lic_type,
                    })
                i += 2
                continue
            i += 1

    # Deduplicate by name
    seen: set[str] = set()
    unique: list[dict] = []
    for lic in licenses:
        if lic["name"].lower() not in seen:
            seen.add(lic["name"].lower())
            unique.append(lic)
    return unique


def _parse_bundles(text: str) -> list[dict]:
    """
    Extract bundle info from lines like:
        EP Bundle Title: EA Platform Bundle
        Debug Bundle Title: EA Platform Bundle, Debug
    """
    bundles: list[dict] = []
    for m in re.finditer(r'(EP|Debug)\s+Bundle Title:\s*([^\n]+)', text, re.IGNORECASE):
        kind = "Debug Bundle" if m.group(1).lower() == "debug" else "EP Bundle"
        name = m.group(2).strip().rstrip(".,")
        if not any(b["name"] == name for b in bundles):
            bundles.append({"name": name, "type": kind})
    return bundles


# ---------------------------------------------------------------------------
# PDF loader (public)
# ---------------------------------------------------------------------------

def _parse_pdf(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    text = _extract_pdf_text(path)

    result = _parse_scalar_fields(text)

    licenses = _parse_licenses(text)
    if licenses:
        result["finite_quantity_licenses"] = licenses

    bundles = _parse_bundles(text)
    if bundles:
        result["bundles"] = bundles

    return result


# ---------------------------------------------------------------------------
# JSON config loader
# ---------------------------------------------------------------------------

def _load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    data.pop("_comment", None)
    return data


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_contract(
    config_path:  str | Path | None = None,
    pdf_path:     str | Path | None = None,
    tc_remaining: int | None = None,
    interactive:  bool = True,
) -> dict[str, Any]:
    """
    Returns a fully-populated contract dict.
    Priority: JSON config > PDF > interactive prompts.
    tc_remaining: if set, used directly (overrides PDF total - used calculation).
    """
    contract: dict[str, Any] = {}

    # 1. JSON config (highest priority)
    if config_path:
        try:
            json_data = _load_json(config_path)
            contract.update({k: v for k, v in json_data.items() if v not in ("", None, [], {})})
            print(f"  Loaded config from {config_path}")
        except FileNotFoundError as e:
            print(f"  [warn] {e}")

    # 2. PDF
    if pdf_path:
        try:
            pdf_data = _parse_pdf(pdf_path)
            for k, v in pdf_data.items():
                if not contract.get(k):   # only fill blanks
                    contract[k] = v
            n_lic = len(contract.get("finite_quantity_licenses", []))
            n_bun = len(contract.get("bundles", []))
            print(f"  Parsed PDF -- {n_lic} license row(s), {n_bun} bundle(s)")
        except Exception as e:
            print(f"  [warn] PDF parse error: {e}")

    # 3. Training credits
    tc_total = int(contract.get("training_credits_total") or 0)
    if tc_remaining is not None:
        contract["training_credits_total"]   = tc_total
        contract["training_credits_used"]    = max(0, tc_total - int(tc_remaining))
        contract["training_credits_remaining"] = int(tc_remaining)
    else:
        contract.setdefault("training_credits_total", 0)
        contract.setdefault("training_credits_used",  0)

    # 4. Interactive prompts for critical blanks
    if interactive:
        for key, label in [
            ("ea_number",     "EA Number (e.g. EA-15647)"),
            ("customer_name", "Customer Name"),
            ("ea_end_date",   "EA End Date (YYYY-MM-DD)"),
        ]:
            if not contract.get(key):
                val = input(f"  Enter {label}: ").strip()
                if val:
                    contract[key] = val

    # Defaults
    contract.setdefault("term_duration",          "N/A")
    contract.setdefault("contract_scope",         "Enterprise Program")
    contract.setdefault("phase",                  "N/A")
    contract.setdefault("technical_support_level","Standard")
    contract.setdefault("bundles",                [])
    contract.setdefault("finite_quantity_licenses", [])

    return contract
