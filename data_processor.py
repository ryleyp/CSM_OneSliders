"""data_processor.py

Parses the three pasted (tab-separated, copied-from-Excel) tables and runs the
three core computations for the EA slide:

  1. Machine Count  -> combine New + Existing into a TOTAL per period, find
     max/min total with the period each occurred, and the average percent
     change period over period.
  2. Locations      -> Top 5 locations by machine count.
  3. Usage Versions -> Top 5 products by total users; for each, the single
     highest-used version and the user count on that version.

Also holds the contract date math (suggested EA End Date + Phase) because those
are pure computations, kept out of the OCR layer.

Everything here is local, in-memory pandas work. No network calls.
"""

from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd

# Month names accepted in dates like "02-JAN-2026".
_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

# Two-letter US state codes, used to split a "City, ST" location string.
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _to_number(value) -> float | None:
    """Pull a number out of messy text, e.g. '20,000' or '142 ' -> 20000 / 142."""
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _is_number(value) -> bool:
    return _to_number(value) is not None


def _split_rows(text: str) -> list[list[str]]:
    """Split a pasted block into rows of cells.

    Splits on tabs (the natural Excel copy delimiter); falls back to runs of
    2+ spaces so the parser still works if tabs were lost in transit.
    """
    rows: list[list[str]] = []
    for raw in (text or "").splitlines():
        if not raw.strip():
            continue
        if "\t" in raw:
            cells = raw.split("\t")
        else:
            cells = re.split(r"\s{2,}", raw.strip())
        cells = [c.strip() for c in cells]
        if any(cells):
            rows.append(cells)
    return rows


def _looks_like_header(cells: list[str], numeric_cols: list[int]) -> bool:
    """A header row has non-numeric text where we expect numbers."""
    for idx in numeric_cols:
        if idx < len(cells) and _is_number(cells[idx]):
            return False
    return True


# --------------------------------------------------------------------------- #
# 1. Machine Count
# --------------------------------------------------------------------------- #
def parse_machine_count(text: str) -> pd.DataFrame:
    """Parse 'period, new, existing' rows into a DataFrame.

    Returns columns: period, new, existing, total.
    Tolerant of an optional header row and of extra columns.
    """
    rows = _split_rows(text)
    records: list[dict] = []
    for i, cells in enumerate(rows):
        if len(cells) < 3:
            continue
        # Skip a header row (first row with non-numeric new/existing cells).
        if i == 0 and _looks_like_header(cells, [1, 2]):
            continue
        period = cells[0]
        new = _to_number(cells[1])
        existing = _to_number(cells[2])
        if not period or new is None or existing is None:
            continue
        records.append(
            {"period": period, "new": new, "existing": existing,
             "total": new + existing}
        )
    return pd.DataFrame(records, columns=["period", "new", "existing", "total"])


def compute_machine_stats(df: pd.DataFrame) -> dict:
    """Max/min total (with period) and average percent change period over period."""
    if df is None or df.empty:
        return {
            "max_total": 0, "max_period": "-",
            "min_total": 0, "min_period": "-",
            "avg_pct_change": 0.0,
        }

    max_idx = df["total"].idxmax()
    min_idx = df["total"].idxmin()

    # Average percent change between consecutive periods.
    pct_changes: list[float] = []
    totals = df["total"].tolist()
    for prev, cur in zip(totals, totals[1:]):
        if prev:
            pct_changes.append((cur - prev) / prev * 100.0)
    avg_pct = sum(pct_changes) / len(pct_changes) if pct_changes else 0.0

    return {
        "max_total": int(df.loc[max_idx, "total"]),
        "max_period": str(df.loc[max_idx, "period"]),
        "min_total": int(df.loc[min_idx, "total"]),
        "min_period": str(df.loc[min_idx, "period"]),
        "avg_pct_change": round(avg_pct, 1),
    }


# --------------------------------------------------------------------------- #
# 2. Locations
# --------------------------------------------------------------------------- #
def _split_location(location: str) -> tuple[str, str]:
    """Best-effort split of a location string into (state, city).

    Handles 'Austin, TX', 'Austin TX', and falls back to (blank, location).
    """
    loc = (location or "").strip()
    if "," in loc:
        city, _, rest = loc.partition(",")
        state = rest.strip().split()[0] if rest.strip() else ""
        return state.upper() if state.upper() in _US_STATES else state, city.strip()
    parts = loc.split()
    if len(parts) >= 2 and parts[-1].upper() in _US_STATES:
        return parts[-1].upper(), " ".join(parts[:-1])
    return "", loc


def parse_locations(text: str) -> pd.DataFrame:
    """Parse 'location, machine count' rows.

    Returns columns: location, state, city, count.
    """
    rows = _split_rows(text)
    records: list[dict] = []
    for i, cells in enumerate(rows):
        if len(cells) < 2:
            continue
        if i == 0 and _looks_like_header(cells, [len(cells) - 1]):
            continue
        location = cells[0]
        count = _to_number(cells[-1])
        if not location or count is None:
            continue
        state, city = _split_location(location)
        records.append(
            {"location": location, "state": state, "city": city,
             "count": int(count)}
        )
    return pd.DataFrame(records, columns=["location", "state", "city", "count"])


def top_locations(df: pd.DataFrame, n: int = 5) -> list[dict]:
    """Top N locations by machine count."""
    if df is None or df.empty:
        return []
    top = df.sort_values("count", ascending=False).head(n)
    return top.to_dict("records")


# --------------------------------------------------------------------------- #
# 3. Usage Versions
# --------------------------------------------------------------------------- #
def parse_usage_versions(text: str) -> pd.DataFrame:
    """Parse 'product, version, user count' rows.

    Returns columns: product, version, users.
    """
    rows = _split_rows(text)
    records: list[dict] = []
    for i, cells in enumerate(rows):
        if len(cells) < 3:
            continue
        if i == 0 and _looks_like_header(cells, [2]):
            continue
        product = cells[0]
        version = cells[1]
        users = _to_number(cells[2])
        if not product or users is None:
            continue
        records.append(
            {"product": product, "version": str(version), "users": int(users)}
        )
    return pd.DataFrame(records, columns=["product", "version", "users"])


def top_versions(df: pd.DataFrame, n: int = 5) -> list[dict]:
    """Top N products by TOTAL users across all versions.

    For each product, report its single highest-used version and the user count
    on THAT version (not the product total). The '%' is that version's share of
    the product's total users.
    """
    if df is None or df.empty:
        return []

    results: list[dict] = []
    totals = df.groupby("product")["users"].sum().sort_values(ascending=False)
    for product in totals.head(n).index:
        sub = df[df["product"] == product]
        top_row = sub.loc[sub["users"].idxmax()]
        product_total = int(totals[product])
        ver_users = int(top_row["users"])
        pct = round(ver_users / product_total * 100.0, 0) if product_total else 0
        results.append(
            {
                "product": product,
                "version": str(top_row["version"]),
                "users": ver_users,
                "product_total": product_total,
                "pct": int(pct),
            }
        )
    return results


# --------------------------------------------------------------------------- #
# Contract date math (suggested EA End Date + Phase)
# --------------------------------------------------------------------------- #
def parse_date(text: str) -> date | None:
    """Parse a date from messy text. Handles '02-JAN-2026', '02/01/2026',
    '2026-01-02', 'January 2, 2026'."""
    if not text:
        return None
    s = str(text).strip()

    m = re.search(r"(\d{1,2})[-\s]([A-Za-z]{3})[A-Za-z]*[-\s](\d{4})", s)
    if m:
        day, mon, year = m.groups()
        mon_num = _MONTHS.get(mon[:3].upper())
        if mon_num:
            try:
                return date(int(year), mon_num, int(day))
            except ValueError:
                pass

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%B %d, %Y",
                "%b %d, %Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_term_years(term_text: str) -> float | None:
    """Pull a number of years out of an EP Term string like '3 years' / '36 months'."""
    if not term_text:
        return None
    s = str(term_text).lower()
    num = _to_number(s)
    if num is None:
        return None
    if "month" in s:
        return num / 12.0
    return num  # assume years otherwise


def add_years(start: date, years: float) -> date:
    """Add a (possibly fractional) number of years to a date."""
    whole = int(years)
    frac_days = int(round((years - whole) * 365))
    try:
        bumped = start.replace(year=start.year + whole)
    except ValueError:  # Feb 29 -> Feb 28
        bumped = start.replace(year=start.year + whole, day=28)
    return bumped + pd.Timedelta(days=frac_days).to_pytimedelta()


def compute_end_date(start: date | None, term_years: float | None) -> date | None:
    """Suggested EA End Date = Start Date + EP Term."""
    if start is None or term_years is None:
        return None
    return add_years(start, term_years)


def compute_phase(start: date | None, term_years: float | None,
                  today: date | None = None) -> dict:
    """Compute phase wording + a 'Year X of N' hint.

    - today before start            -> 'Not started'
    - today after computed end       -> 'Expired'
    - <50% of term elapsed           -> 'First Half'
    - >=50% elapsed                  -> 'Second Half'
    """
    today = today or date.today()
    end = compute_end_date(start, term_years)
    if start is None or term_years is None or end is None:
        return {"phase": "", "hint": "", "fraction": None}

    if today < start:
        return {"phase": "Not started", "hint": "Term has not begun",
                "fraction": 0.0}
    if today > end:
        return {"phase": "Expired", "hint": "Past end date", "fraction": 1.0}

    total_days = (end - start).days or 1
    elapsed_days = (today - start).days
    fraction = elapsed_days / total_days

    phase = "First Half" if fraction < 0.5 else "Second Half"

    n = int(round(term_years)) or 1
    year_x = min(int(elapsed_days / 365) + 1, n)
    hint = f"Year {year_x} of {n}"

    return {"phase": phase, "hint": hint, "fraction": round(fraction, 3)}
