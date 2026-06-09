"""
Generates CSM insights as a prioritized markdown report.
Pure local computation — no LLM, no network calls.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _today() -> date:
    return date.today()


def _parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            pass
    return None


def _trend_direction(totals: list[float]) -> str:
    if len(totals) < 2:
        return "insufficient data"
    increases = sum(1 for i in range(1, len(totals)) if totals[i] > totals[i - 1])
    decreases = sum(1 for i in range(1, len(totals)) if totals[i] < totals[i - 1])
    if increases > decreases:
        return "upward"
    if decreases > increases:
        return "downward"
    return "flat"


def generate_insights(
    data: dict[str, Any],
    contract: dict[str, Any],
) -> str:
    lines: list[str] = []
    findings: list[tuple[int, str]] = []   # (priority_score, text)

    ea_num      = contract.get("ea_number", "N/A")
    customer    = contract.get("customer_name", "N/A")
    ea_end_raw  = contract.get("ea_end_date", "")
    ea_end      = _parse_date(str(ea_end_raw)) if ea_end_raw else None

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    lines.append(f"# CSM Insights — {customer} ({ea_num})")
    lines.append(f"_Generated {_today().isoformat()} | Fully offline, zero network calls_")
    lines.append("")

    # -----------------------------------------------------------------------
    # Renewal context
    # -----------------------------------------------------------------------
    if ea_end:
        days_to_renewal = (ea_end - _today()).days
        renewal_note = (
            f"EA expires **{ea_end.isoformat()}** — "
            + (
                f"**{days_to_renewal} days away** (RENEWAL WINDOW ACTIVE)"
                if days_to_renewal <= 180
                else f"{days_to_renewal} days away"
            )
        )
        priority = 10 if days_to_renewal <= 180 else 3
        findings.append((priority, f"**Renewal Context:** {renewal_note}"))
    else:
        findings.append((2, "**Renewal Context:** EA end date not provided — confirm with customer."))

    # -----------------------------------------------------------------------
    # Machines / Usage trend
    # -----------------------------------------------------------------------
    machines = data.get("machines")
    if machines:
        totals   = machines["totals"]
        periods  = machines["periods"]
        direction = _trend_direction(totals)
        avg_chg   = machines["avg_pct_change"]
        max_p, max_s = machines["max_period"], machines["max_sessions"]
        min_p, min_s = machines["min_period"], machines["min_sessions"]

        trend_text = (
            f"**Adoption Trend ({direction}):** "
            f"Avg QoQ change {avg_chg:+.1f}%. "
            f"Peak: {max_s:,} sessions in {max_p}. "
            f"Trough: {min_s:,} sessions in {min_p}."
        )
        score = 8 if direction == "downward" else (6 if direction == "upward" else 5)
        findings.append((score, trend_text))

        # New vs Existing churn signal
        nve = machines.get("new_vs_existing", {})
        if nve:
            new_ct  = nve.get("New", 0)
            exist_ct = nve.get("Existing", 0)
            total_ct = new_ct + exist_ct
            if total_ct > 0:
                new_pct  = round(new_ct / total_ct * 100, 1)
                exist_pct = round(exist_ct / total_ct * 100, 1)
                if exist_pct < 60:
                    churn_signal = (
                        f"**Churn Risk (New/Existing Mix):** "
                        f"Only {exist_pct:.1f}% existing users ({exist_ct:,}) vs "
                        f"{new_pct:.1f}% new ({new_ct:,}). "
                        "Low existing-user retention may indicate adoption friction."
                    )
                    findings.append((7, churn_signal))
                else:
                    findings.append((3, (
                        f"**New/Existing Mix:** {exist_pct:.1f}% existing / "
                        f"{new_pct:.1f}% new — healthy retention signal."
                    )))

    # -----------------------------------------------------------------------
    # Software — license utilization & version health
    # -----------------------------------------------------------------------
    software = data.get("software")
    licenses = contract.get("finite_quantity_licenses", [])
    license_map = {lic["name"].lower(): lic["count"] for lic in licenses}

    if software:
        for prod in software["products"]:
            pname  = prod["product"]
            pusage = prod["usage"]
            lic_count = license_map.get(pname.lower())

            if lic_count:
                util_pct = round(pusage / lic_count * 100, 1)
                if util_pct >= 90:
                    findings.append((9, (
                        f"**Upsell Opportunity — {pname}:** "
                        f"{pusage:,} sessions vs {lic_count:,} licensed seats "
                        f"({util_pct:.1f}% utilization). Near or over limit — discuss expansion."
                    )))
                elif util_pct <= 30:
                    findings.append((8, (
                        f"**Adoption Risk — {pname}:** "
                        f"Only {pusage:,} sessions vs {lic_count:,} licensed seats "
                        f"({util_pct:.1f}% utilization). Low usage — engagement needed."
                    )))
                else:
                    findings.append((4, (
                        f"**License Utilization — {pname}:** "
                        f"{pusage:,} / {lic_count:,} seats used ({util_pct:.1f}%)."
                    )))

        # Version health
        vb = software.get("version_breakdown", [])
        if vb:
            # Detect products where the highest-used version looks old
            # (heuristic: if there are 3+ versions, old = not the top two)
            product_versions: dict[str, list[dict]] = {}
            for row in vb:
                product_versions.setdefault(row["product"], []).append(row)

            for product, rows in product_versions.items():
                if len(rows) >= 3:
                    top_ver = rows[0]["version"]
                    old_usage = sum(r["usage"] for r in rows[2:])
                    total_prod = sum(r["usage"] for r in rows)
                    old_pct = round(old_usage / total_prod * 100, 1) if total_prod else 0
                    if old_pct >= 20:
                        findings.append((6, (
                            f"**Version Health — {product}:** "
                            f"{old_pct:.1f}% of usage is on versions older than the top two "
                            f"(current top: {top_ver}). Upgrade conversation recommended."
                        )))

    # -----------------------------------------------------------------------
    # Training credits
    # -----------------------------------------------------------------------
    tc_total = int(contract.get("training_credits_total") or 0)
    tc_used  = int(contract.get("training_credits_used") or 0)
    if tc_total > 0:
        tc_remaining = tc_total - tc_used
        tc_pct = round(tc_used / tc_total * 100, 1)
        if tc_pct <= 25:
            findings.append((7, (
                f"**Unused Training Credits:** {tc_remaining} of {tc_total} credits unused "
                f"({100 - tc_pct:.1f}% remaining). "
                "Schedule training sessions before EA renewal to maximize value."
            )))
        elif tc_pct >= 90:
            findings.append((5, (
                f"**Training Credits Nearly Exhausted:** {tc_used} of {tc_total} used "
                f"({tc_pct:.1f}%). Consider requesting additional credits at renewal."
            )))
        else:
            findings.append((3, (
                f"**Training Credits:** {tc_used}/{tc_total} used ({tc_pct:.1f}%). "
                f"{tc_remaining} remaining."
            )))

    # -----------------------------------------------------------------------
    # Geographic concentration
    # -----------------------------------------------------------------------
    cities = data.get("cities")
    if cities:
        locs  = cities["top_locations"]
        total = cities["total_usage"]
        if locs:
            top_pct = locs[0]["pct_of_total"]
            if top_pct >= 50:
                findings.append((5, (
                    f"**Geographic Concentration:** {locs[0]['label']} accounts for "
                    f"{top_pct:.1f}% of all usage ({locs[0]['usage']:,} of {total:,} sessions). "
                    "High concentration; explore expansion to secondary sites."
                )))
            else:
                findings.append((2, (
                    f"**Geographic Distribution:** Usage is spread across locations; "
                    f"top site {locs[0]['label']} at {top_pct:.1f}% ({locs[0]['usage']:,} sessions)."
                )))

    # -----------------------------------------------------------------------
    # Sort findings by priority descending and format
    # -----------------------------------------------------------------------
    findings.sort(key=lambda x: x[0], reverse=True)

    lines.append("## Prioritized Findings")
    lines.append("")
    for i, (score, text) in enumerate(findings, start=1):
        lines.append(f"### {i}. {text}")
        lines.append("")

    # -----------------------------------------------------------------------
    # Data summary appendix
    # -----------------------------------------------------------------------
    lines.append("---")
    lines.append("## Data Summary")
    lines.append("")

    if machines:
        lines.append("### Machine Sessions by Period")
        for p, t in zip(machines["periods"], machines["totals"]):
            lines.append(f"- {p}: {t:,}")
        lines.append("")

    if software:
        lines.append("### Software Usage")
        for prod in software["products"]:
            lines.append(
                f"- {prod['product']}: {prod['usage']:,} sessions "
                f"({prod['pct_of_total']}% of total) — top version: {prod['top_version']}"
            )
        lines.append("")

    if cities:
        lines.append(f"### Top {cities['top_n']} Locations")
        for loc in cities["top_locations"]:
            lines.append(f"- {loc['label']}: {loc['usage']:,} ({loc['pct_of_total']}%)")
        lines.append("")

    return "\n".join(lines)
