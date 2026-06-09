"""
Detects and processes the three tab types from CSV or multi-tab XLSX.
No network calls. Pure pandas computation.
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
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    """Return first column name that fuzzy-matches any candidate keyword (whole-word preferred)."""
    import re as _re
    # First pass: whole-word match (avoids "count" matching inside "country")
    for col in df.columns:
        for cand in candidates:
            if _re.search(r'\b' + _re.escape(cand) + r'\b', col):
                return col
    # Second pass: substring fallback for multi-word column names
    for col in df.columns:
        for cand in candidates:
            if cand in col and len(cand) >= 4:
                return col
    return None


# ---------------------------------------------------------------------------
# Tab detection
# ---------------------------------------------------------------------------

def _is_machines_tab(df: pd.DataFrame) -> bool:
    cols = set(df.columns)
    has_machine_type = any("machine" in c for c in cols)
    has_year_or_quarter = any(k in cols for k in ("year", "quarter", "qtr", "month"))
    return has_machine_type and has_year_or_quarter


def _is_software_tab(df: pd.DataFrame) -> bool:
    cols = set(df.columns)
    has_product = any("product" in c or "software" in c for c in cols)
    has_version = any("version" in c for c in cols)
    return has_product or has_version


def _is_cities_tab(df: pd.DataFrame) -> bool:
    cols = set(df.columns)
    has_geo = any(k in cols for k in ("city", "country", "location", "region", "site"))
    return has_geo


# ---------------------------------------------------------------------------
# Machines processing
# ---------------------------------------------------------------------------

def process_machines(df: pd.DataFrame) -> dict[str, Any]:
    df = _normalise_cols(df.copy())

    year_col     = _find_col(df, "year")
    quarter_col  = _find_col(df, "quarter", "qtr")
    month_col    = _find_col(df, "month")
    type_col     = _find_col(df, "machine type", "type")
    count_col    = _find_col(df, "count", "sessions", "machines", "usage", "qty", "quantity")

    if not count_col:
        raise ValueError("Machines tab: cannot find a count/sessions column.")

    df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)

    # Build a unified period label for charting
    if quarter_col and year_col:
        df["_period"] = df[year_col].astype(str) + " " + df[quarter_col].astype(str)
    elif month_col and year_col:
        df["_period"] = df[year_col].astype(str) + "-" + df[month_col].astype(str)
    elif quarter_col:
        df["_period"] = df[quarter_col].astype(str)
    elif month_col:
        df["_period"] = df[month_col].astype(str)
    else:
        df["_period"] = "Period"

    # Total = New + Existing per period (ignore machine_type column value)
    quarterly = (
        df.groupby("_period", sort=False)[count_col].sum().reset_index()
    )
    quarterly.columns = ["period", "total"]

    # Preserve order that appeared in the file
    seen: list[str] = []
    for p in df["_period"]:
        if p not in seen:
            seen.append(p)
    quarterly = quarterly.set_index("period").reindex(seen).reset_index()

    totals = quarterly["total"].tolist()
    periods = quarterly["period"].tolist()

    max_idx = int(quarterly["total"].idxmax())
    min_idx = int(quarterly["total"].idxmin())

    # Quarter-over-quarter % changes
    pct_changes: list[float] = []
    for i in range(1, len(totals)):
        if totals[i - 1] != 0:
            pct_changes.append(round((totals[i] - totals[i - 1]) / totals[i - 1] * 100, 1))
    avg_pct_change = round(sum(pct_changes) / len(pct_changes), 1) if pct_changes else 0.0

    # New vs Existing mix (for churn signal)
    new_vs_existing: dict[str, int] = {}
    if type_col:
        mix = df.groupby(df[type_col].str.strip().str.title())[count_col].sum()
        new_vs_existing = mix.to_dict()

    # Monthly totals if we have month data
    monthly_totals: dict[str, int] = {}
    if month_col:
        mt = df.groupby(df[month_col].astype(str))[count_col].sum()
        monthly_totals = mt.to_dict()

    return {
        "periods": periods,
        "totals": totals,
        "max_period": periods[max_idx],
        "max_sessions": int(totals[max_idx]),
        "min_period": periods[min_idx],
        "min_sessions": int(totals[min_idx]),
        "avg_pct_change": avg_pct_change,
        "new_vs_existing": new_vs_existing,
        "monthly_totals": monthly_totals,
    }


# ---------------------------------------------------------------------------
# Software processing
# ---------------------------------------------------------------------------

def process_software(df: pd.DataFrame) -> dict[str, Any]:
    df = _normalise_cols(df.copy())

    product_col = _find_col(df, "product", "software", "application", "app")
    version_col = _find_col(df, "version", "ver", "release")
    count_col   = _find_col(df, "count", "usage", "sessions", "qty", "quantity", "uses")

    if not product_col:
        raise ValueError("Software tab: cannot find a product column.")
    if not count_col:
        raise ValueError("Software tab: cannot find a usage count column.")

    df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)

    total_usage = df[count_col].sum()

    # Usage per product
    by_product = df.groupby(product_col)[count_col].sum().sort_values(ascending=False)

    # Highest-used version per product
    top_versions: dict[str, str] = {}
    if version_col:
        for product, grp in df.groupby(product_col):
            top_row = grp.loc[grp[count_col].idxmax()]
            top_versions[str(product)] = str(top_row[version_col])

    products_data: list[dict] = []
    for product, usage in by_product.items():
        pct = round(usage / total_usage * 100, 1) if total_usage else 0.0
        products_data.append({
            "product": str(product),
            "usage": int(usage),
            "pct_of_total": pct,
            "top_version": top_versions.get(str(product), "N/A"),
        })

    # Version breakdown (for version health analysis)
    version_breakdown: list[dict] = []
    if version_col:
        by_version = (
            df.groupby([product_col, version_col])[count_col]
            .sum()
            .reset_index()
            .sort_values(count_col, ascending=False)
        )
        for _, row in by_version.iterrows():
            version_breakdown.append({
                "product": str(row[product_col]),
                "version": str(row[version_col]),
                "usage": int(row[count_col]),
            })

    return {
        "products": products_data,
        "total_usage": int(total_usage),
        "version_breakdown": version_breakdown,
    }


# ---------------------------------------------------------------------------
# Cities processing
# ---------------------------------------------------------------------------

def process_cities(df: pd.DataFrame, top_n: int = 5) -> dict[str, Any]:
    df = _normalise_cols(df.copy())

    city_col    = _find_col(df, "city", "location", "site")
    country_col = _find_col(df, "country", "region", "nation")
    count_col   = _find_col(df, "count", "usage", "sessions", "qty", "quantity", "uses")

    if not count_col:
        raise ValueError("Cities tab: cannot find a usage count column.")

    df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)

    group_cols = [c for c in [country_col, city_col] if c]
    if not group_cols:
        raise ValueError("Cities tab: cannot find city or country column.")

    by_city = (
        df.groupby(group_cols, as_index=False)[count_col]
        .sum()
        .sort_values(count_col, ascending=False)
    )

    total = by_city[count_col].sum()
    top = by_city.head(top_n)

    locations: list[dict] = []
    for _, row in top.iterrows():
        label_parts = [str(row[c]) for c in group_cols]
        locations.append({
            "label": ", ".join(label_parts),
            "usage": int(row[count_col]),
            "pct_of_total": round(row[count_col] / total * 100, 1) if total else 0.0,
        })

    return {
        "top_locations": locations,
        "total_usage": int(total),
        "top_n": top_n,
    }


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load_data(path: str | Path, top_cities: int = 5) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    suffix = path.suffix.lower()

    frames: list[pd.DataFrame] = []
    if suffix == ".csv":
        frames = [pd.read_csv(path)]
    elif suffix in (".xlsx", ".xls"):
        xl = pd.ExcelFile(path, engine="openpyxl")
        frames = [xl.parse(sheet) for sheet in xl.sheet_names]
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use .csv or .xlsx")

    result: dict[str, Any] = {}

    for df in frames:
        norm = _normalise_cols(df.copy())
        if "machines" not in result and _is_machines_tab(norm):
            try:
                result["machines"] = process_machines(df)
            except Exception as e:
                print(f"  [warn] machines tab skipped: {e}")
        if "software" not in result and _is_software_tab(norm):
            try:
                result["software"] = process_software(df)
            except Exception as e:
                print(f"  [warn] software tab skipped: {e}")
        if "cities" not in result and _is_cities_tab(norm):
            try:
                result["cities"] = process_cities(df, top_n=top_cities)
            except Exception as e:
                print(f"  [warn] cities tab skipped: {e}")

    return result
