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
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    """Return first column that matches any candidate keyword (whole-word first, then substring)."""
    # Pass 1: whole-word boundary match
    for col in df.columns:
        for cand in candidates:
            if re.search(r'\b' + re.escape(cand) + r'\b', col):
                return col
    # Pass 2: substring match (length >= 4 to avoid "count" in "country" etc.)
    for col in df.columns:
        for cand in candidates:
            if len(cand) >= 4 and cand in col:
                return col
    return None


def _col_has_values(df: pd.DataFrame, col: str, *values: str) -> bool:
    """Check whether a column contains any of the given string values (case-insensitive)."""
    try:
        vals = df[col].dropna().astype(str).str.strip().str.lower().unique()
        return any(v.lower() in vals for v in values)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tab detection  (scored so the best match wins)
# ---------------------------------------------------------------------------

def _machines_score(df: pd.DataFrame) -> int:
    score = 0
    cols = set(df.columns)
    # Time columns
    if any(k in cols for k in ("year", "quarter", "qtr")):
        score += 3
    if "month" in cols:
        score += 2
    # Machine-type column
    if any("machine" in c for c in cols):
        score += 4
    # New/Existing values anywhere
    for col in df.columns:
        if _col_has_values(df, col, "new", "existing"):
            score += 5
            break
    # Generic count column
    if any(k in c for c in cols for k in ("count", "session", "usage")):
        score += 2
    return score


def _software_score(df: pd.DataFrame) -> int:
    score = 0
    cols = set(df.columns)
    if any("product" in c or "software" in c or "application" in c for c in cols):
        score += 5
    if any("version" in c or " ver" in c or c.startswith("ver") for c in cols):
        score += 4
    if any(k in c for c in cols for k in ("count", "usage", "session")):
        score += 2
    return score


def _cities_score(df: pd.DataFrame) -> int:
    score = 0
    cols = set(df.columns)
    if "city" in cols:
        score += 6
    if "country" in cols:
        score += 4
    if any(k in cols for k in ("location", "site", "region")):
        score += 3
    if any(k in c for c in cols for k in ("count", "usage", "session")):
        score += 2
    return score


def _detect_tab_type(df: pd.DataFrame) -> str | None:
    norm = _normalise_cols(df)
    scores = {
        "machines": _machines_score(norm),
        "software": _software_score(norm),
        "cities":   _cities_score(norm),
    }
    best_type, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score < 4:
        return None
    # Require at least 2-point lead over the runner-up to avoid false positives
    others = [s for t, s in scores.items() if t != best_type]
    if best_score - max(others) < 2:
        # Tie-break: machines requires time column, software requires product/version
        if best_type == "machines" and scores["machines"] >= 5:
            return "machines"
        if best_type == "software" and scores["software"] >= 6:
            return "software"
        return None
    return best_type


# ---------------------------------------------------------------------------
# Machines processing
# ---------------------------------------------------------------------------

def process_machines(df: pd.DataFrame) -> dict[str, Any]:
    df = _normalise_cols(df)

    year_col    = _find_col(df, "year")
    quarter_col = _find_col(df, "quarter", "qtr")
    month_col   = _find_col(df, "month")
    type_col    = _find_col(df, "machine type", "type")
    count_col   = _find_col(df, "session", "count", "machines", "usage", "qty", "quantity", "users", "seats")

    if not count_col:
        # Last resort: pick first numeric column that isn't a time/type column
        time_cols = {c for c in [year_col, quarter_col, month_col, type_col] if c}
        for col in df.columns:
            if col not in time_cols:
                if pd.to_numeric(df[col], errors="coerce").notna().sum() > 0:
                    count_col = col
                    break
    if not count_col:
        raise ValueError("Machines tab: cannot find a count/sessions column.")

    df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)

    # Build period label
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

    # Preserve original row order
    seen: list[str] = []
    for p in df["_period"]:
        if p not in seen:
            seen.append(p)
    quarterly = quarterly.set_index("period").reindex(seen).reset_index()
    quarterly["total"] = pd.to_numeric(quarterly["total"], errors="coerce").fillna(0)

    totals  = quarterly["total"].tolist()
    periods = quarterly["period"].tolist()

    if not totals:
        raise ValueError("Machines tab: no data after grouping.")

    max_idx = int(quarterly["total"].idxmax())
    min_idx = int(quarterly["total"].idxmin())

    pct_changes: list[float] = []
    for i in range(1, len(totals)):
        if totals[i - 1] != 0:
            pct_changes.append(round((totals[i] - totals[i - 1]) / totals[i - 1] * 100, 1))
    avg_pct_change = round(sum(pct_changes) / len(pct_changes), 1) if pct_changes else 0.0

    new_vs_existing: dict[str, int] = {}
    if type_col:
        try:
            mix = df.groupby(df[type_col].astype(str).str.strip().str.title())[count_col].sum()
            new_vs_existing = {str(k): int(v) for k, v in mix.items()}
        except Exception:
            pass

    monthly_totals: dict[str, int] = {}
    if month_col:
        try:
            mt = df.groupby(df[month_col].astype(str))[count_col].sum()
            monthly_totals = {str(k): int(v) for k, v in mt.items()}
        except Exception:
            pass

    return {
        "periods":        periods,
        "totals":         [float(t) for t in totals],
        "max_period":     periods[max_idx],
        "max_sessions":   int(totals[max_idx]),
        "min_period":     periods[min_idx],
        "min_sessions":   int(totals[min_idx]),
        "avg_pct_change": avg_pct_change,
        "new_vs_existing": new_vs_existing,
        "monthly_totals": monthly_totals,
    }


# ---------------------------------------------------------------------------
# Software processing
# ---------------------------------------------------------------------------

def process_software(df: pd.DataFrame) -> dict[str, Any]:
    df = _normalise_cols(df)

    product_col = _find_col(df, "product", "software", "application", "app", "name")
    version_col = _find_col(df, "version", "ver", "release")
    count_col   = _find_col(df, "count", "usage", "session", "qty", "quantity", "uses", "users")

    if not product_col:
        raise ValueError("Software tab: cannot find a product column.")
    if not count_col:
        raise ValueError("Software tab: cannot find a usage count column.")

    df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)
    total_usage   = df[count_col].sum()

    by_product = df.groupby(product_col)[count_col].sum().sort_values(ascending=False)

    top_versions: dict[str, str] = {}
    if version_col:
        for product, grp in df.groupby(product_col):
            top_row = grp.loc[grp[count_col].idxmax()]
            top_versions[str(product)] = str(top_row[version_col])

    products_data: list[dict] = []
    for product, usage in by_product.items():
        pct = round(usage / total_usage * 100, 1) if total_usage else 0.0
        products_data.append({
            "product":     str(product),
            "usage":       int(usage),
            "pct_of_total": pct,
            "top_version": top_versions.get(str(product), "N/A"),
        })

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
    }


# ---------------------------------------------------------------------------
# Cities processing
# ---------------------------------------------------------------------------

def process_cities(df: pd.DataFrame, top_n: int = 5) -> dict[str, Any]:
    df = _normalise_cols(df)

    city_col    = _find_col(df, "city", "location", "site")
    country_col = _find_col(df, "country", "region", "nation")
    count_col   = _find_col(df, "count", "usage", "session", "qty", "quantity", "uses", "users")

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
    top   = by_city.head(top_n)

    locations: list[dict] = []
    for _, row in top.iterrows():
        label_parts = [str(row[c]) for c in group_cols]
        locations.append({
            "label":        ", ".join(label_parts),
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

def load_data(path: str | Path, top_cities: int = 5) -> dict[str, Any]:
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
                    result["software"] = process_software(df)
                elif tab_type == "cities":
                    result["cities"]   = process_cities(df, top_n=top_cities)
            except Exception as e:
                print(f"  [warn] {tab_type} tab skipped: {e}")

    return result
