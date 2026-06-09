"""insights.py

Pure-local CSM insight generation. No LLM, no network — just arithmetic over
the reviewed slide data, turned into a prioritized list of plain-English bullets
grounded in specific numbers.

Coverage (per spec):
  - adoption trend direction from the total machine line
  - new vs existing mix as a churn signal
  - license utilization vs finite license counts (upsell / adoption risk)
  - version health (most users on an old version -> upgrade conversation)
  - unused FLEX / training credits
  - location concentration
  - everything tied back to the EA end date for renewal context

Each insight is a dict: {priority, category, text}. Lower priority = higher
urgency. app.py renders them in priority order.
"""

from __future__ import annotations


def _fmt_int(n) -> str:
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return str(n)


def generate_insights(data: dict) -> list[dict]:
    """Build the prioritized CSM insight list from reviewed slide data."""
    insights: list[dict] = []

    machine = data.get("machine", {})
    stats = machine.get("stats", {})
    df = machine.get("df")
    finite = data.get("finite_licenses", []) or []
    versions = data.get("versions_top5", []) or []
    locations = data.get("locations_top5", []) or []
    credits = data.get("credits", {}) or {}
    end_date = data.get("ea_end_date", "")
    phase = data.get("phase", "")
    customer = data.get("customer", "the customer")

    renewal_tag = f" Tie this to the EA end date ({end_date})." if end_date else ""

    # --- 1. Adoption trend direction from the total line -------------------- #
    avg_change = stats.get("avg_pct_change", 0.0)
    if df is not None and not getattr(df, "empty", True):
        first_total = int(df["total"].iloc[0])
        last_total = int(df["total"].iloc[-1])
        if avg_change > 1.0:
            insights.append({
                "priority": 3,
                "category": "Adoption trend",
                "text": (f"Healthy growth: total machines rose from "
                         f"{_fmt_int(first_total)} to {_fmt_int(last_total)} "
                         f"(avg +{avg_change:.1f}% per period). Expansion story "
                         f"supports a strong renewal." + renewal_tag),
            })
        elif avg_change < -1.0:
            insights.append({
                "priority": 1,
                "category": "Adoption trend",
                "text": (f"RISK — declining usage: total machines fell from "
                         f"{_fmt_int(first_total)} to {_fmt_int(last_total)} "
                         f"(avg {avg_change:.1f}% per period). Investigate churn "
                         f"before renewal." + renewal_tag),
            })
        else:
            insights.append({
                "priority": 2,
                "category": "Adoption trend",
                "text": (f"Flat usage: total machines roughly steady around "
                         f"{_fmt_int(last_total)} (avg {avg_change:+.1f}% per "
                         f"period). Look for an expansion lever." + renewal_tag),
            })

    # --- 2. New vs existing mix (churn signal) ------------------------------ #
    if df is not None and not getattr(df, "empty", True) and "new" in df:
        last_new = int(df["new"].iloc[-1])
        last_existing = int(df["existing"].iloc[-1])
        last_total = last_new + last_existing
        if last_total:
            new_pct = last_new / last_total * 100.0
            if new_pct < 10:
                insights.append({
                    "priority": 2,
                    "category": "New vs existing",
                    "text": (f"Churn signal: only {new_pct:.0f}% of current "
                             f"machines are new ({_fmt_int(last_new)} new vs "
                             f"{_fmt_int(last_existing)} existing). Low new-seat "
                             f"flow weakens the expansion case."),
                })
            elif new_pct > 40:
                insights.append({
                    "priority": 3,
                    "category": "New vs existing",
                    "text": (f"Strong onboarding: {new_pct:.0f}% of machines are "
                             f"new ({_fmt_int(last_new)} new vs "
                             f"{_fmt_int(last_existing)} existing) — active "
                             f"rollout in progress."),
                })

    # --- 3. License utilization vs finite counts --------------------------- #
    total_finite = sum(int(r.get("count", 0)) for r in finite)
    last_total_machines = stats.get("max_total", 0)
    if df is not None and not getattr(df, "empty", True):
        last_total_machines = int(df["total"].iloc[-1])
    if total_finite:
        util = (last_total_machines / total_finite * 100.0) if total_finite else 0
        if util >= 90:
            insights.append({
                "priority": 1,
                "category": "License utilization",
                "text": (f"UPSELL — near/over capacity: ~{_fmt_int(last_total_machines)} "
                         f"machines against {_fmt_int(total_finite)} finite "
                         f"licenses ({util:.0f}% utilized). Raise an expansion "
                         f"conversation." + renewal_tag),
            })
        elif util <= 40:
            insights.append({
                "priority": 2,
                "category": "License utilization",
                "text": (f"ADOPTION RISK — low utilization: ~{_fmt_int(last_total_machines)} "
                         f"machines against {_fmt_int(total_finite)} finite "
                         f"licenses ({util:.0f}% utilized). Drive adoption to "
                         f"protect the renewal." + renewal_tag),
            })

    # --- 4. Version health -------------------------------------------------- #
    for v in versions[:3]:
        pct = v.get("pct", 0)
        ver = str(v.get("version", ""))
        # Heuristic: an "old" version dominating usage is an upgrade trigger.
        if pct >= 60 and _looks_old(ver):
            insights.append({
                "priority": 2,
                "category": "Version health",
                "text": (f"Upgrade conversation: {pct}% of {v['product']} users "
                         f"({_fmt_int(v['users'])}) are on {ver}, an older "
                         f"release. Plan an upgrade path."),
            })

    # --- 5. Unused FLEX / training credits ---------------------------------- #
    purchased = _num(credits.get("purchased"))
    used = _num(credits.get("used"))
    if purchased and purchased > 0:
        used = used or 0
        pct_used = used / purchased * 100.0
        unused = purchased - used
        if pct_used < 50:
            insights.append({
                "priority": 1 if pct_used < 25 else 2,
                "category": "Training credits",
                "text": (f"Unused value: only {pct_used:.0f}% of "
                         f"{_fmt_int(purchased)} FLEX/training credits used "
                         f"({_fmt_int(unused)} remaining). Schedule training to "
                         f"burn credits before they expire." + renewal_tag),
            })

    # --- 6. Location concentration ------------------------------------------ #
    if locations:
        total_loc_machines = sum(int(l.get("count", 0)) for l in locations)
        top = locations[0]
        if total_loc_machines:
            top_pct = int(top.get("count", 0)) / total_loc_machines * 100.0
            if top_pct >= 50:
                label = top.get("city") or top.get("location") or "the top site"
                insights.append({
                    "priority": 3,
                    "category": "Location concentration",
                    "text": (f"Concentration risk: {label} holds {top_pct:.0f}% "
                             f"of machines across the top sites. A single-site "
                             f"dependency is a renewal risk — broaden the "
                             f"footprint."),
                })

    # --- 7. Renewal context anchor ------------------------------------------ #
    if end_date:
        phase_note = f" Currently {phase}." if phase else ""
        insights.append({
            "priority": 4,
            "category": "Renewal context",
            "text": (f"EA for {customer} ends {end_date}.{phase_note} Align the "
                     f"actions above to a renewal/expansion plan ahead of that "
                     f"date."),
        })

    insights.sort(key=lambda x: x["priority"])
    return insights


def _looks_old(version: str) -> bool:
    """Crude 'is this an old version' check: a leading year/major < current-ish,
    or any version at all when we can't tell. Used only as an upgrade hint."""
    import re
    m = re.search(r"(\d{4})", version)
    if m:
        return int(m.group(1)) <= 2022
    m = re.search(r"^(\d+)", version)
    if m:
        return int(m.group(1)) < 20  # NI-style yearly majors (e.g. 21.x, 22.x)
    return False


def _num(value):
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None
