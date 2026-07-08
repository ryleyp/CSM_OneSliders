"""profiles.py

Local account profiles for EA Slide Builder.

A profile captures everything the user entered for one account — the three
pasted tables (raw text, re-parsed on load so parser improvements apply
retroactively), the reviewed contract fields, the finite-license rows, and the
bundle names — as a JSON file in ./profiles next to the app.

Quarterly refresh workflow: load the profile, paste the new machine table,
generate. Fully local: profiles never leave the machine.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

PROFILES_DIR = Path(__file__).parent / "profiles"

# The widget-backed session_state keys a profile carries.
FIELD_KEYS = [
    "f_service_id", "f_customer", "f_start_date", "f_ep_term",
    "f_end_date", "f_phase", "f_phase_hint", "f_contract_scope", "f_debug",
    "f_support_tier", "f_support_scope", "f_systemlink_snow",
    "f_flex_purchased", "f_flex_used",
]
TEXT_KEYS = ["machine_text", "locations_text", "versions_text"]


def _safe_name(name: str) -> str:
    """Make a profile name filesystem-safe."""
    name = re.sub(r"[^\w\- ]+", "", (name or "").strip())
    name = re.sub(r"\s+", "_", name)
    return name or "profile"


def suggest_name(state: dict) -> str:
    """Default profile name from the reviewed Service ID + customer."""
    sid = str(state.get("f_service_id", "") or "").strip()
    cust = str(state.get("f_customer", "") or "").strip()
    base = " ".join(p for p in (sid, cust) if p)
    return _safe_name(base) if base else "profile"


def list_profiles() -> list[str]:
    """Sorted names of saved profiles (without .json)."""
    if not PROFILES_DIR.is_dir():
        return []
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def profile_path(name: str) -> Path:
    return PROFILES_DIR / f"{_safe_name(name)}.json"


def save_profile(name: str, state: dict, finite_rows: list[dict],
                 bundles: list[str]) -> Path:
    """Write the current inputs to ./profiles/<name>.json and return the path."""
    PROFILES_DIR.mkdir(exist_ok=True)
    payload = {
        "version": 1,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "texts": {k: str(state.get(k, "") or "") for k in TEXT_KEYS},
        "fields": {
            k: bool(state.get(k, False)) if k == "f_systemlink_snow"
            else str(state.get(k, "") or "")
            for k in FIELD_KEYS
        },
        "finite_licenses": [
            {
                "count": int(r.get("count") or 0),
                "license_type": str(r.get("license_type") or ""),
                "license_name": str(r.get("license_name") or ""),
            }
            for r in finite_rows
        ],
        "bundles": [str(b) for b in bundles],
    }
    path = profile_path(name)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_profile(name: str) -> dict | None:
    """Read a profile by name; None if missing/corrupt."""
    path = profile_path(name)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("texts", {})
    data.setdefault("fields", {})
    data["fields"].setdefault("f_systemlink_snow", False)
    data.setdefault("finite_licenses", [])
    data.setdefault("bundles", [])
    return data


def delete_profile(name: str) -> bool:
    path = profile_path(name)
    if path.is_file():
        path.unlink()
        return True
    return False
