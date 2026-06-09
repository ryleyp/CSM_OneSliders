"""
Loads contract info from (in priority order):
  1. JSON config file
  2. PDF parsed locally with pdfplumber + regex
  3. Interactive prompts for remaining blank fields
No network calls.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Field definitions
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    ("ea_number",           "EA Number (e.g. EA-123456)"),
    ("customer_name",       "Customer Name"),
    ("ea_end_date",         "EA End Date (YYYY-MM-DD)"),
    ("term_duration",       "Term Duration (e.g. 3 Years)"),
    ("contract_scope",      "Contract Scope (e.g. Enterprise)"),
    ("phase",               "Phase (e.g. Phase 2)"),
]

OPTIONAL_FIELDS = [
    ("training_credits_total", "Training Credits Total"),
    ("training_credits_used",  "Training Credits Used"),
    ("technical_support_level","Technical Support Level"),
]

# ---------------------------------------------------------------------------
# JSON loader
# ---------------------------------------------------------------------------

def _load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    # Strip internal comment key
    data.pop("_comment", None)
    return data


# ---------------------------------------------------------------------------
# PDF parser
# ---------------------------------------------------------------------------

_PDF_PATTERNS: list[tuple[str, str]] = [
    ("ea_number",     r"EA[- ]?(\d{5,8})"),
    ("ea_end_date",   r"(?:end\s+date|expir\w+)[:\s]+(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})"),
    ("term_duration", r"(?:term|duration)[:\s]+([\d]+\s+years?)"),
    ("customer_name", r"(?:customer|client|account)[:\s]+([A-Za-z0-9&., ]{3,60})"),
    ("contract_scope",r"(?:scope)[:\s]+([A-Za-z ]{3,40})"),
    ("phase",         r"(?:phase)[:\s]+([A-Za-z0-9 ]{1,20})"),
    ("training_credits_total", r"training\s+credits?[:\s]+(\d+)"),
]


def _parse_pdf(path: str | Path) -> dict[str, Any]:
    """Extract contract fields from PDF using pdfplumber + regex. Offline only."""
    try:
        import pdfplumber
    except ImportError:
        print("  [warn] pdfplumber not installed; skipping PDF parsing.")
        return {}

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

    result: dict[str, Any] = {}
    for field, pattern in _PDF_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            value = m.group(1).strip().rstrip(".,;")
            if field == "ea_number" and not value.startswith("EA-"):
                value = "EA-" + value
            result[field] = value

    return result


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def _prompt_missing(contract: dict[str, Any]) -> dict[str, Any]:
    """Ask user for any required fields that are still blank."""
    for key, label in REQUIRED_FIELDS:
        if not contract.get(key):
            val = input(f"  Enter {label}: ").strip()
            if val:
                contract[key] = val

    for key, label in OPTIONAL_FIELDS:
        if contract.get(key) in (None, ""):
            val = input(f"  Enter {label} (or press Enter to skip): ").strip()
            if val:
                contract[key] = val if not val.isdigit() else int(val)

    return contract


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_contract(
    config_path: str | Path | None = None,
    pdf_path: str | Path | None = None,
    interactive: bool = True,
) -> dict[str, Any]:
    """
    Returns a dict with all contract fields populated.
    Priority: JSON config > PDF > interactive prompts.
    """
    contract: dict[str, Any] = {}

    # --- 1. JSON config ---
    if config_path:
        try:
            json_data = _load_json(config_path)
            contract.update({k: v for k, v in json_data.items() if v not in ("", None)})
            print(f"  Loaded contract config from {config_path}")
        except FileNotFoundError as e:
            print(f"  [warn] {e}")

    # --- 2. PDF ---
    if pdf_path:
        try:
            pdf_data = _parse_pdf(pdf_path)
            for k, v in pdf_data.items():
                if not contract.get(k):   # only fill blanks
                    contract[k] = v
            print(f"  Parsed PDF contract data from {pdf_path}")
        except FileNotFoundError as e:
            print(f"  [warn] {e}")

    # --- 3. Interactive prompts ---
    missing_required = [k for k, _ in REQUIRED_FIELDS if not contract.get(k)]
    if missing_required and interactive:
        print(f"  Missing required fields: {', '.join(missing_required)}")
        contract = _prompt_missing(contract)

    # Defaults for optional numeric fields
    contract.setdefault("training_credits_total", 0)
    contract.setdefault("training_credits_used", 0)
    contract.setdefault("technical_support_level", "Standard")
    contract.setdefault("bundles", [])
    contract.setdefault("finite_quantity_licenses", [])

    return contract
