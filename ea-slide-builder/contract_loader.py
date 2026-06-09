"""
Loads contract info from a PDF (pdfplumber + regex) then fills blanks
interactively. JSON config still supported as an override layer.
No network calls.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# PDF parser
# ---------------------------------------------------------------------------

# Patterns are tried in order; first match wins for each field.
_PDF_PATTERNS: list[tuple[str, str]] = [
    ("ea_number",      r"EA[- #]?(\d{5,9})"),
    ("customer_name",  r"(?:sold\s+to|bill\s+to|customer|account\s+name|company)[:\s]+([A-Za-z0-9&.,'\- ]{3,60})"),
    ("ea_end_date",    r"(?:end\s+date|expir\w+|subscription\s+end)[:\s]+(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"),
    ("term_duration",  r"(?:term|subscription\s+term|duration)[:\s]+([\d]+[\s\-]*years?)"),
    ("contract_scope", r"(?:scope|coverage)[:\s]+([A-Za-z ]{3,40})"),
    ("phase",          r"(?:phase)[:\s]+([\w ]{1,20})"),
    ("training_credits_total", r"(?:training\s+credits?|flex\s+credits?)[:\s]+(\d+)"),
]

# Patterns for extracting license rows from a PDF table
# Matches lines like:  "500  AutoCAD  Named User"  or  "AutoCAD LT  250  Subscription"
_LICENSE_LINE_PATTERNS = [
    # qty at start: "500 AutoCAD Named User Subscription"
    re.compile(r"^(\d{1,6})\s{1,6}([A-Za-z][A-Za-z0-9 &.+\-]{2,50}?)\s{2,}(.{3,30}?)$", re.M),
    # qty at end: "AutoCAD  Named User  500"
    re.compile(r"^([A-Za-z][A-Za-z0-9 &.+\-]{2,50}?)\s{2,}(.{3,30}?)\s{2,}(\d{1,6})$", re.M),
]

_BUNDLE_KEYWORDS = ["bundle", "suite", "collection", "cloud"]


def _parse_pdf(path: str | Path) -> dict[str, Any]:
    try:
        import pdfplumber
    except ImportError:
        print("  [warn] pdfplumber not installed; skipping PDF parsing.")
        return {}

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    full_text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    result: dict[str, Any] = {}

    # --- Scalar fields ---
    for field, pattern in _PDF_PATTERNS:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            value = m.group(1).strip().rstrip(".,;")
            if field == "ea_number" and not value.upper().startswith("EA"):
                value = "EA-" + value
            result[field] = value

    # --- License rows ---
    licenses: list[dict] = []
    bundles:  list[dict] = []

    for pattern in _LICENSE_LINE_PATTERNS:
        for m in pattern.finditer(full_text):
            groups = [g.strip() for g in m.groups()]
            # Determine which group is the quantity
            if groups[0].isdigit():
                qty, name, lic_type = int(groups[0]), groups[1], groups[2]
            elif groups[2].isdigit():
                name, lic_type, qty = groups[0], groups[1], int(groups[2])
            else:
                continue

            # Skip noise lines (headers, page numbers, totals)
            skip_words = {"qty", "quantity", "product", "type", "total", "page", "date", "item"}
            if name.lower() in skip_words or lic_type.lower() in skip_words:
                continue
            if qty == 0:
                continue

            # Classify as bundle or license
            name_lower = name.lower()
            if any(kw in name_lower for kw in _BUNDLE_KEYWORDS):
                if not any(b["name"].lower() == name_lower for b in bundles):
                    bundles.append({"name": name, "type": lic_type})
            else:
                if not any(l["name"].lower() == name_lower for l in licenses):
                    licenses.append({"count": qty, "name": name, "type": lic_type})

    if licenses:
        result["finite_quantity_licenses"] = licenses
    if bundles:
        result["bundles"] = bundles

    return result


# ---------------------------------------------------------------------------
# JSON config loader (optional override layer)
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
    config_path: str | Path | None = None,
    pdf_path:    str | Path | None = None,
    tc_remaining: int | None = None,
    interactive: bool = True,
) -> dict[str, Any]:
    """
    Returns a fully-populated contract dict.
    Priority order: JSON config > PDF > interactive prompts.
    tc_remaining: if provided, overrides training_credits_used calculation.
    """
    contract: dict[str, Any] = {}

    # 1. JSON config (highest priority)
    if config_path:
        try:
            json_data = _load_json(config_path)
            contract.update({k: v for k, v in json_data.items() if v not in ("", None, [], {})})
            print(f"  Loaded contract config from {config_path}")
        except FileNotFoundError as e:
            print(f"  [warn] {e}")

    # 2. PDF
    if pdf_path:
        try:
            pdf_data = _parse_pdf(pdf_path)
            for k, v in pdf_data.items():
                if not contract.get(k):
                    contract[k] = v
            n_lic = len(contract.get("finite_quantity_licenses", []))
            print(f"  Parsed PDF — found {n_lic} license row(s)")
        except FileNotFoundError as e:
            print(f"  [warn] {e}")

    # 3. Training credits: if caller supplied tc_remaining, derive used from total
    tc_total = int(contract.get("training_credits_total") or 0)
    if tc_remaining is not None:
        contract["training_credits_total"] = tc_total
        contract["training_credits_used"]  = max(0, tc_total - int(tc_remaining))
        contract["training_credits_remaining"] = int(tc_remaining)
    else:
        contract.setdefault("training_credits_total", 0)
        contract.setdefault("training_credits_used",  0)

    # 4. Interactive prompts for critical missing fields
    required = [
        ("ea_number",      "EA Number (e.g. EA-123456)"),
        ("customer_name",  "Customer Name"),
        ("ea_end_date",    "EA End Date (YYYY-MM-DD)"),
    ]
    if interactive:
        for key, label in required:
            if not contract.get(key):
                val = input(f"  Enter {label}: ").strip()
                if val:
                    contract[key] = val

    # Defaults
    contract.setdefault("term_duration",         "N/A")
    contract.setdefault("contract_scope",        "N/A")
    contract.setdefault("phase",                 "N/A")
    contract.setdefault("technical_support_level", "Standard")
    contract.setdefault("bundles",               [])
    contract.setdefault("finite_quantity_licenses", [])

    return contract
