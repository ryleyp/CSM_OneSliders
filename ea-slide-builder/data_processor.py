"""
Detects and processes the three tab types from CSV or multi-tab XLSX.
No network calls. Pure pandas computation.

Handles real-world Tableau/BI export column names like:
  "Year of session_date", "Distinct count of machine_id", "ip_city", etc.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _has_col_containing(cols: list[str], *keywords: str) -> bool:
    """True if any column name contains any of the keywords as a substring."""
    return any(kw in col for col in cols for kw in keywords)


def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    """
    Return the first column whose name contains any candidate keyword.
    Tries whole-word regex first (more precise), then plain substring.
    """
    # Pass 1 — whole-word regex (e.g. "year" matches "year of session_date")
    for col in df.columns:
        for cand in candidates:
            if re.search(r'\b' + re.escape(cand) + r'\b', col, re.IGNORECASE):
                return col
    # Pass 2 — substring (handles "ip_city", "product_version", etc.)
    for col in df.columns:
        for cand in candidates:
            if len(cand) >= 4 and cand.lower() in col.lower():
                return col
    return None


# ---------------------------------------------------------------------------
# Tab detection — scored so the best match wins
# ---------------------------------------------------------------------------

def _machines_score(cols: list[str]) -> int:
    score = 0
    if _has_col_containing(cols, "machine"):
        score += 4
    # Time dimension columns
    if _has_col_containing(cols, "year"):
        score += 3
    if _has_col_containing(cols, "quarter", "qtr"):
        score += 3
    if _has_col_containing(cols, "month"):
        score += 2
    # Count column
    if _has_col_containing(cols, "count", "session", "machine_id"):
        score += 2
    return score


def _software_score(cols: list[str]) -> int:
    score = 0
    if _has_col_containing(cols, "product", "software", "application"):
        score += 5
    if _has_col_containing(cols, "version", "ver"):
        score += 4
    if _has_col_containing(cols, "count", "usage", "session", "machine_id"):
        score += 2
    return score


def _cities_score(cols: list[str]) -> int:
    score = 0
    if _has_col_containing(cols, "city"):
        score += 6
    if _has_col_containing(cols, "country"):
        score += 5
    if _has_col_containing(cols, "region", "state", "province"):
        score += 3
    if _has_col_containing(cols, "count", "value", "session", "machine_id"):
        score += 2
    return score


def _detect_tab_type(df: pd.DataFrame) -> str | None:
    cols = [str(c).strip().lower() for c in df.columns]
    scores = {
        "machines": _machines_score(cols),
        "software": _software_score(cols),
        "cities":   _cities_score(cols),
    }
    best, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score < 4:
        return None
    others = [s for t, s in scores.items() if t != best]
    if best_score - max(others) < 2:
        # Tie-break heuristics
        if best == "machines" and best_score >= 6:
            return "machines"
        if best == "software" and scores["software"] >= 7:
            return "software"
        return None
    return best


# ---------------------------------------------------------------------------
# Machines processing
# ---------------------------------------------------------------------------

def process_machines(df: pd.DataFrame) -> dict[str, Any]:
    df = _normalise_cols(df)

    year_col    = _find_col(df, "year")
    quarter_col = _find_col(df, "quarter", "qtr")
    month_col   = _find_col(df, "month")
    type_col    = _find_col(df, "machine type", "type")
    # Search for count column, excluding already-identified structural columns
    _skip = {c for c in [year_col, quarter_col, month_col, type_col] if c}
    df_for_count = df.drop(columns=list(_skip), errors="ignore")
    count_col = _find_col(df_for_count, "machine_id", "session", "count",
                          "usage", "qty", "quantity", "users", "seats", "values")
    if not count_col:
        for col in df.columns:
            if col not in _skip and pd.to_numeric(df[col], errors="coerce").notna().mean() > 0.5:
                count_col = col
                break
    if not count_col:
        raise ValueError("Machines tab: no count/sessions column found.")

    df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)

    # Build period label — prefer Year+Quarter, fall back to Year+Month, etc.
    if quarter_col and year_col:
        df["_period"] = df[year_col].astype(str) + " " + df[quarter_col].astype(str)
    elif month_col and year_col:
        df["_period"] = df[year_col].astype(str) + "-" + df[month_col].astype(str)
    elif quarter_col:
        df["_period"] = df[quarter_col].astype(str)
    elif month_col:
        df["_period"] = df[month_col].astype(str)
    elif year_col:
        df["_period"] = df[year_col].astype(str)
    else:
        df["_period"] = "Period"

    # Sum New + Existing per period
    quarterly = df.groupby("_period", sort=False)[count_col].sum().reset_index()
    quarterly.columns = ["period", "total"]

    # Preserve the order periods first appeared in the file
    seen: list[str] = []
    for p in df["_period"]:
        if p not in seen:
            seen.append(p)
    quarterly = quarterly.set_index("period").reindex(seen).reset_index()
    quarterly["total"] = pd.to_numeric(quarterly["total"], errors="coerce").fillna(0)

    totals  = quarterly["total"].tolist()
    periods = quarterly["period"].tolist()

    if not totals:
        raise ValueError("Machines tab: no data rows after grouping.")

    max_idx = int(quarterly["total"].idxmax())
    min_idx = int(quarterly["total"].idxmin())

    pct_changes: list[float] = []
    for i in range(1, len(totals)):
        prev = totals[i - 1]
        if prev != 0:
            pct_changes.append(round((totals[i] - prev) / prev * 100, 1))
    avg_pct_change = round(sum(pct_changes) / len(pct_changes), 1) if pct_changes else 0.0

    new_vs_existing: dict[str, int] = {}
    if type_col:
        try:
            mix = df.groupby(df[type_col].astype(str).str.strip().str.title())[count_col].sum()
            new_vs_existing = {str(k): int(v) for k, v in mix.items()}
        except Exception:
            pass

    return {
        "periods":         periods,
        "totals":          [float(t) for t in totals],
        "max_period":      periods[max_idx],
        "max_sessions":    int(totals[max_idx]),
        "min_period":      periods[min_idx],
        "min_sessions":    int(totals[min_idx]),
        "avg_pct_change":  avg_pct_change,
        "new_vs_existing": new_vs_existing,
    }


# ---------------------------------------------------------------------------
# Software processing
# ---------------------------------------------------------------------------

def process_software(df: pd.DataFrame, top_versions: int | None = None) -> dict[str, Any]:
    """
    top_versions: limit the number of PRODUCTS shown in the Version Usage table.
                  None = show all products.
    """
    df = _normalise_cols(df)

    product_col = _find_col(df, "product", "software", "application", "app", "name")
    version_col = _find_col(df, "version", "ver", "release")
    _skip_sw    = {c for c in [product_col, version_col] if c}
    df_for_count = df.drop(columns=list(_skip_sw), errors="ignore")
    count_col   = _find_col(df_for_count, "machine_id", "count", "usage", "session",
                             "qty", "quantity", "uses", "users", "values")

    if not product_col:
        raise ValueError("Software tab: no product column found.")
    if not count_col:
        raise ValueError("Software tab: no usage count column found.")

    df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)
    total_usage   = df[count_col].sum()

    by_product = df.groupby(product_col)[count_col].sum().sort_values(ascending=False)

    # Map each product to its top version (the version with highest usage)
    top_version_map: dict[str, tuple[str, int]] = {}
    if version_col:
        for product, grp in df.groupby(product_col):
            top_row = grp.loc[grp[count_col].idxmax()]
            top_version_map[str(product)] = (
                str(top_row[version_col]),
                int(top_row[count_col]),
            )

    products_data: list[dict] = []
    for product, usage in by_product.items():
        pct = round(usage / total_usage * 100, 1) if total_usage else 0.0
        tv, tv_usage = top_version_map.get(str(product), ("N/A", 0))
        products_data.append({
            "product":      str(product),
            "usage":        int(usage),
            "pct_of_total": pct,
            "top_version":  tv,
        })

    # top_version_rows: top N products, each with their single best version row
    # Used by slide_builder for the Version Usage table
    top_n_products = products_data if top_versions is None else products_data[:top_versions]
    top_version_rows: list[dict] = []
    for p in top_n_products:
        tv, tv_usage = top_version_map.get(p["product"], ("N/A", 0))
        tv_pct = round(tv_usage / p["usage"] * 100, 0) if p["usage"] else 0.0
        top_version_rows.append({
            "product":           p["product"],
            "top_version":       tv,
            "top_version_usage": tv_usage,
            "top_version_pct":   tv_pct,
        })

    # Full version breakdown (all products, all versions) — kept for compatibility
    version_breakdown: list[dict] = []
    if version_col:
        by_ver = (
            df.groupby([product_col, version_col])[count_col]
            .sum()
            .reset_index()
            .sort_values(count_col, ascending=False)
        )
        for _, row in by_ver.iterrows():
            version_breakdown.append({
                "product": str(row[product_col]),
                "version": str(row[version_col]),
                "usage":   int(row[count_col]),
            })

    return {
        "products":          products_data,
        "total_usage":       int(total_usage),
        "version_breakdown": version_breakdown,
        "top_version_rows":  top_version_rows,
        "top_versions":      top_versions,
    }


# ---------------------------------------------------------------------------
# Cities processing
# ---------------------------------------------------------------------------

def process_cities(df: pd.DataFrame, top_n: int = 5) -> dict[str, Any]:
    df = _normalise_cols(df)

    city_col    = _find_col(df, "city")
    country_col = _find_col(df, "country")
    region_col  = _find_col(df, "region", "state", "province")

    # Identify the count column, but skip columns already claimed as geo columns
    _geo_cols = {c for c in [city_col, country_col, region_col] if c}
    df_for_count = df.drop(columns=list(_geo_cols), errors="ignore")
    count_col_found = _find_col(df_for_count, "values", "machine_id", "session",
                                "usage", "qty", "quantity", "users")
    # Fallback: any numeric column not in geo_cols
    if not count_col_found:
        for col in df.columns:
            if col not in _geo_cols and pd.to_numeric(df[col], errors="coerce").notna().mean() > 0.5:
                count_col_found = col
                break
    count_col = count_col_found

    if not count_col:
        raise ValueError("Cities tab: no count column found.")

    df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)

    # If a product/measure column exists, filter to aggregate rows ("*")
    # so we don't double-count machines that use multiple products
    product_col = _find_col(df, "product_name", "product", "software")
    if product_col and df[product_col].astype(str).str.strip().eq("*").any():
        df = df[df[product_col].astype(str).str.strip() == "*"].copy()

    # Also handle Measure Names filter column if present
    measure_names_col = _find_col(df, "measure names", "measure name")
    if measure_names_col:
        # Keep only the primary count measure
        counts_mask = df[measure_names_col].astype(str).str.lower().str.contains("count|machine_id|session")
        if counts_mask.any():
            df = df[counts_mask].copy()

    group_cols = [c for c in [country_col, city_col] if c]
    if not group_cols:
        raise ValueError("Cities tab: no city or country column found.")

    by_city = (
        df.groupby(group_cols, as_index=False)[count_col]
        .sum()
        .sort_values(count_col, ascending=False)
    )

    total = by_city[count_col].sum()
    top   = by_city.head(top_n)

    locations: list[dict] = []
    for _, row in top.iterrows():
        label_parts = [str(row[c]) for c in group_cols]
        locations.append({
            "label":        ", ".join(label_parts),
            "country":      str(row[country_col]) if country_col else "",
            "region":       str(row[region_col])  if region_col  else "",
            "city":         str(row[city_col])    if city_col    else "",
            "usage":        int(row[count_col]),
            "pct_of_total": round(row[count_col] / total * 100, 1) if total else 0.0,
        })

    return {
        "top_locations": locations,
        "total_usage":   int(total),
        "top_n":         top_n,
    }


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load_data(path: str | Path, top_cities: int = 5, top_versions: int | None = None) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        frames = [pd.read_csv(path)]
    elif suffix in (".xlsx", ".xls"):
        xl     = pd.ExcelFile(path, engine="openpyxl")
        frames = [xl.parse(sheet) for sheet in xl.sheet_names]
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    result: dict[str, Any] = {}

    for df in frames:
        if df.empty or len(df.columns) < 2:
            continue
        tab_type = _detect_tab_type(df)
        if tab_type and tab_type not in result:
            try:
                if tab_type == "machines":
                    result["machines"] = process_machines(df)
                elif tab_type == "software":
                    result["software"] = process_software(df, top_versions=top_versions)
                elif tab_type == "cities":
                    result["cities"]   = process_cities(df, top_n=top_cities)
            except Exception as e:
                print(f"  [warn] {tab_type} tab skipped: {e}")

    return result
