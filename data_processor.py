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
from datetime import date, datetime, timedelta

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
    """Parse a machine-count paste into period / new / existing / total rows.

    Supports two layouts and auto-detects which one was pasted:

    1. LONG / tidy (Tableau-style), one row per month x machine type, e.g.
         Year of session_date | Quarter | Month | Machine Type | Distinct count
         2021 | Q1 | March | Existing | 363
       These are rolled up to QUARTERLY periods (the slide reports an
       "avg quarterly increase"). A quarter's value is the AVERAGE of its
       monthly distinct counts, since machines recur month to month and summing
       them would double-count.

    2. WIDE, one row per period: period | new | existing.

    Returns columns: period, new, existing, total (chronological order).
    """
    rows = _split_rows(text)
    if _is_long_machine_format(rows):
        return _parse_machine_long(rows)
    return _parse_machine_wide(rows)


def _is_long_machine_format(rows: list[list[str]]) -> bool:
    """Long format has a 'Machine Type' column whose values are New/Existing."""
    for cells in rows:
        if len(cells) < 4:
            continue
        joined = " ".join(c.lower() for c in cells)
        if "machine type" in joined:
            return True
        # A standalone New/Existing cell alongside >=4 columns => long format.
        if any(re.fullmatch(r"(new|existing)", c.strip(), re.IGNORECASE)
               for c in cells):
            return True
    return False


def _month_num(text: str) -> int | None:
    if not text:
        return None
    return _MONTHS.get(str(text).strip()[:3].upper())


def _parse_machine_long(rows: list[list[str]]) -> pd.DataFrame:
    """Roll a long/tidy export up to quarterly new/existing/total averages."""
    if not rows:
        return pd.DataFrame(columns=["period", "new", "existing", "total"])

    # Locate columns. Use header keywords when the first row is a header,
    # otherwise fall back to the canonical positional order.
    header = rows[0]
    has_header = not _is_number(header[-1])
    year_i, month_i, quarter_i, type_i, count_i = 0, 2, 1, 3, len(header) - 1
    if has_header:
        for i, h in enumerate(header):
            hl = h.lower()
            if "year" in hl:
                year_i = i
            elif "quarter" in hl:
                quarter_i = i
            elif "month" in hl:
                month_i = i
            elif "machine type" in hl or hl.strip() == "type" or "type" in hl:
                type_i = i
            elif any(k in hl for k in ("count", "machine_id", "distinct")):
                count_i = i
        data_rows = rows[1:]
    else:
        data_rows = rows

    # Aggregate counts by (year, quarter) -> month -> {new, existing}.
    buckets: dict[tuple[int, int], dict[int, dict[str, float]]] = {}
    for cells in data_rows:
        if len(cells) <= max(year_i, month_i, type_i, count_i):
            continue
        year = _to_number(cells[year_i])
        mnum = _month_num(cells[month_i])
        if mnum is None and quarter_i < len(cells):
            # Fall back to the quarter column if month is missing/garbled.
            qm = re.search(r"[1-4]", cells[quarter_i])
            if qm:
                mnum = (int(qm.group(0)) - 1) * 3 + 2  # mid-quarter month
        count = _to_number(cells[count_i])
        if year is None or mnum is None or count is None:
            continue
        mtype = cells[type_i].strip().lower()
        if "new" in mtype:
            key = "new"
        elif "exist" in mtype:
            key = "existing"
        else:
            continue
        quarter = (mnum - 1) // 3 + 1
        bucket = buckets.setdefault((int(year), quarter), {})
        month_entry = bucket.setdefault(mnum, {"new": 0.0, "existing": 0.0})
        month_entry[key] += count

    # Average each quarter's monthly snapshots into one value per period.
    records: list[dict] = []
    for (year, quarter) in sorted(buckets):
        months = buckets[(year, quarter)]
        n_months = len(months) or 1
        new_q = round(sum(m["new"] for m in months.values()) / n_months)
        exist_q = round(sum(m["existing"] for m in months.values()) / n_months)
        records.append({
            "period": f"Q{quarter} {year}",
            "new": new_q,
            "existing": exist_q,
            "total": new_q + exist_q,
            "_months": n_months,
        })

    # Drop trailing INCOMPLETE quarters (e.g. a current quarter still in
    # progress with fewer months than a full one) so a partial period doesn't
    # masquerade as the min on the trend. Only trims from the end, and keys on
    # month-completeness, never on the value itself.
    if records:
        full = max(r["_months"] for r in records)
        while len(records) > 1 and records[-1]["_months"] < full:
            records.pop()
    for r in records:
        r.pop("_months", None)

    return pd.DataFrame(records, columns=["period", "new", "existing", "total"])


def _parse_machine_wide(rows: list[list[str]]) -> pd.DataFrame:
    """Wide layout: one row per period -> period | new | existing."""
    records: list[dict] = []
    for i, cells in enumerate(rows):
        if len(cells) < 3:
            continue
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
# Full US state name -> 2-letter code, so the slide's STATE column stays compact
# when the export gives a full region name (e.g. "Connecticut" -> "CT").
_STATE_NAME_TO_CODE = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}


def _abbrev_state(region: str) -> str:
    """Map a region to a 2-letter code when possible, else return it trimmed."""
    r = (region or "").strip()
    if r.upper() in _US_STATES:
        return r.upper()
    return _STATE_NAME_TO_CODE.get(r.lower(), r)


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


def parse_locations(text: str, *, avoid_product_double_count: bool = True) -> pd.DataFrame:
    """Parse a locations paste into location / state / city / count rows.

    Supports two layouts, auto-detected:

    1. GEO export (Tableau-style), one row per city (and product), e.g.
         ip_country | ip_region | ip_city | Measure Names | product_name | Measure Values
         United States | Connecticut | Bristol | Distinct count of machine_id | LabVIEW | 1
       Machine counts are grouped per (region, city); ip_region becomes the
       state (abbreviated when it's a US state name). When the export is split
       by product, the default is to use the largest product row per site
       instead of summing product rows, which avoids counting the same machines
       multiple times.

    2. SIMPLE: location | machine count.

    Returns columns: location, state, city, count.
    """
    rows = _split_rows(text)
    if _is_geo_location_format(rows):
        return _parse_locations_geo(
            rows,
            avoid_product_double_count=avoid_product_double_count,
        )
    return _parse_locations_simple(rows)


def _is_geo_location_format(rows: list[list[str]]) -> bool:
    """Geo export has ip_region / ip_city (or a Measure Values column)."""
    if not rows:
        return False
    header = " ".join(c.lower() for c in rows[0])
    if ("ip_city" in header or "ip_region" in header
            or ("measure value" in header and "city" in header)):
        return True
    # Headerless Tableau copy: country | region | city | measure | product | value.
    for cells in rows[:5]:
        if len(cells) >= 5 and _to_number(cells[-1]) is not None:
            joined = " ".join(c.lower() for c in cells[:-1])
            if any(k in joined for k in ("machine", "distinct", "count")):
                return True
    return False


def _parse_locations_geo(
    rows: list[list[str]],
    *,
    avoid_product_double_count: bool = True,
) -> pd.DataFrame:
    """Aggregate a geo export to machines per (region, city)."""
    first = rows[0]
    has_header = any(
        key in " ".join(c.lower() for c in first)
        for key in ("ip_", "measure value", "measure name", "product_name", "city")
    ) and _to_number(first[-1]) is None
    data_rows = rows[1:] if has_header else rows
    region_i = city_i = value_i = None
    product_i = measure_i = None
    if has_header:
        header = rows[0]
        for i, h in enumerate(header):
            hl = h.lower()
            if "region" in hl or hl.endswith("state") or hl == "state":
                region_i = i
            elif "city" in hl:
                city_i = i
            elif "product" in hl:
                product_i = i
            elif "measure name" in hl:
                measure_i = i
            elif "measure value" in hl or "(measure)" in hl or "count" in hl:
                value_i = i
    else:
        # Headerless export order: country, region, city, measure, product, value.
        region_i, city_i, measure_i, product_i, value_i = 1, 2, 3, 4, len(first) - 1
    if city_i is None:
        return _parse_locations_simple(rows)
    if value_i is None:
        value_i = len(first) - 1  # Measure Values is the last column

    agg: dict[tuple[str, str], int] = {}
    use_max_per_site = avoid_product_double_count and product_i is not None
    required_cols = [i for i in (region_i, city_i, value_i, measure_i) if i is not None]
    for cells in data_rows:
        if len(cells) <= max(required_cols):
            continue
        if measure_i is not None and len(cells) > measure_i:
            measure = cells[measure_i].lower()
            if measure and not any(
                k in measure for k in ("machine", "distinct", "count")
            ):
                continue
        region = cells[region_i].strip() if region_i is not None else ""
        city = cells[city_i].strip()
        count = _to_number(cells[value_i])
        if not city or count is None:
            continue
        if _looks_like_non_site(city):
            continue
        key = (region, city)
        count_i = int(count)
        if use_max_per_site:
            agg[key] = max(agg.get(key, 0), count_i)
        else:
            agg[key] = agg.get(key, 0) + count_i

    records: list[dict] = []
    for (region, city), count in agg.items():
        state = _abbrev_state(region)
        location = f"{city}, {state}" if state else city
        records.append({"location": location, "state": state, "city": city,
                        "count": count})
    return pd.DataFrame(records, columns=["location", "state", "city", "count"])


def _parse_locations_simple(rows: list[list[str]]) -> pd.DataFrame:
    """Simple layout: location | machine count."""
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
        if _looks_like_non_site(city or location):
            continue
        records.append(
            {"location": location, "state": state, "city": city,
             "count": int(count)}
        )
    return pd.DataFrame(records, columns=["location", "state", "city", "count"])


def _looks_like_non_site(value: str) -> bool:
    """Reject subtotal/date/header values that are not actual site names."""
    text = (value or "").strip()
    if not text:
        return True
    low = text.lower()
    if low in {"*", "all", "total", "grand total", "subtotal", "null", "none"}:
        return True
    if re.fullmatch(r"\d{4}(?:\s+q[1-4])?", low):
        return True
    if re.fullmatch(r"q[1-4](?:\s+\d{4})?", low):
        return True
    if low in {"new", "existing", "machine type", "product_name", "product version"}:
        return True
    return False


def top_locations(df: pd.DataFrame, n: int = 5) -> list[dict]:
    """Top N locations by machine count."""
    if df is None or df.empty:
        return []
    usable = df[
        df["city"].fillna("").map(lambda v: not _looks_like_non_site(str(v)))
    ].copy()
    if usable.empty:
        return []
    top = usable.sort_values("count", ascending=False).head(n)
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
    """Suggested EA End Date = the inclusive final day of the EP term.

    For example, a 3-year term beginning 02-JAN-2026 runs through
    01-JAN-2029, not 02-JAN-2029.
    """
    if start is None or term_years is None:
        return None
    return add_years(start, term_years) - timedelta(days=1)


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
