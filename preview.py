"""preview.py

On-page HTML preview of the EA one-slider.

Renders a faithful miniature of the slide (same layout, colors, and data as
slide_builder.py) as self-contained HTML/CSS/SVG, so the user can review the
slide before downloading the .pptx. Pure string building — no network, no JS
dependencies.
"""

from __future__ import annotations

import html

DARK = "#013324"
ACCENT = "#18af7c"
TINT = "#ecf7f2"
BORDER = "#dddddd"
GRAY = "#6e6e6e"
MUTED = "#8fc9b6"
TREND = "#b5d6c9"


def _e(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _fmt(value) -> str:
    try:
        return f"{int(str(value).replace(',', '')):,}"
    except (ValueError, TypeError):
        return _e(value)


# --------------------------------------------------------------------------- #
# SVG line chart (single series + dashed trend + peak marker)
# --------------------------------------------------------------------------- #
def _chart_svg(df, width=340, height=210) -> str:
    if df is None or getattr(df, "empty", True):
        return f'<div class="empty">No machine-count data</div>'
    periods = [str(p) for p in df["period"].tolist()]
    totals = [float(t) for t in df["total"].tolist()]
    n = len(totals)
    pad_l, pad_r, pad_t, pad_b = 34, 8, 8, 20
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b
    lo, hi = min(totals), max(totals)
    span = (hi - lo) or 1.0
    lo -= span * 0.08
    hi += span * 0.08
    span = hi - lo

    def x(i):
        return pad_l + (iw * i / max(n - 1, 1))

    def y(v):
        return pad_t + ih * (1 - (v - lo) / span)

    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(totals))

    # Least-squares trend (matches the .pptx chart).
    trend_line = ""
    if n >= 3:
        xs = list(range(n))
        mx, my = sum(xs) / n, sum(totals) / n
        denom = sum((i - mx) ** 2 for i in xs) or 1
        slope = sum((i - mx) * (v - my) for i, v in zip(xs, totals)) / denom
        y0, y1 = my + slope * (0 - mx), my + slope * (n - 1 - mx)
        trend_line = (f'<line x1="{x(0):.1f}" y1="{y(y0):.1f}" '
                      f'x2="{x(n-1):.1f}" y2="{y(y1):.1f}" stroke="{TREND}" '
                      f'stroke-width="1.5" stroke-dasharray="5,4"/>')

    peak_i = totals.index(max(totals))
    gridlines = "".join(
        f'<line x1="{pad_l}" y1="{pad_t + ih * f:.1f}" x2="{width - pad_r}" '
        f'y2="{pad_t + ih * f:.1f}" stroke="#f0f0f0" stroke-width="1"/>'
        for f in (0.0, 0.5, 1.0))
    x_labels = (
        f'<text x="{x(0):.0f}" y="{height - 5}" font-size="8" fill="{GRAY}" '
        f'text-anchor="start">{_e(periods[0])}</text>'
        f'<text x="{x(n-1):.0f}" y="{height - 5}" font-size="8" fill="{GRAY}" '
        f'text-anchor="end">{_e(periods[-1])}</text>')
    y_labels = (
        f'<text x="{pad_l - 4}" y="{y(max(totals)):.0f}" font-size="8" '
        f'fill="{GRAY}" text-anchor="end">{_fmt(int(max(totals)))}</text>'
        f'<text x="{pad_l - 4}" y="{y(min(totals)) + 3:.0f}" font-size="8" '
        f'fill="{GRAY}" text-anchor="end">{_fmt(int(min(totals)))}</text>')

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Total machines over time">'
        f"{gridlines}{trend_line}"
        f'<polyline points="{pts}" fill="none" stroke="{ACCENT}" '
        f'stroke-width="2.5" stroke-linejoin="round"/>'
        f'<circle cx="{x(peak_i):.1f}" cy="{y(totals[peak_i]):.1f}" r="5" '
        f'fill="{ACCENT}" stroke="#ffffff" stroke-width="2"/>'
        f"{x_labels}{y_labels}</svg>"
    )


# --------------------------------------------------------------------------- #
# Card fragments
# --------------------------------------------------------------------------- #
def _card(title, body, extra_class="") -> str:
    return (f'<div class="card {extra_class}">'
            f'<div class="ctitle">{_e(title)}</div>'
            f'<div class="card-body">{body}</div></div>')


def _contract_card(data) -> str:
    rows = [("EA End Date", data.get("ea_end_date")),
            ("Term Duration", data.get("ep_term")),
            ("Contract Scope", data.get("contract_scope")),
            ("Phase", data.get("phase"))]
    body = "".join(
        f'<div class="krow"><span class="k">{_e(k)}</span>'
        f'<span class="v">{_e(v) or "&mdash;"}</span></div>'
        for k, v in rows)
    return _card("Contract Details", body, "contract-card")


def _bundles_card(data) -> str:
    bundles = data.get("bundles", []) or []
    if not bundles:
        return _card("Bundle Information", '<div class="empty">No bundles provided</div>')
    pills = "".join(f'<div class="pill">{_e(b)}</div>' for b in bundles[:5])
    return _card("Bundle Information", pills)


def _finite_card(data) -> str:
    rows = data.get("finite_licenses", []) or []
    if not rows:
        return _card("NI SW Licenses (Finite Qty)",
                     '<div class="empty">No finite licenses provided</div>')
    density = " ultra-dense" if len(rows) > 8 else " dense" if len(rows) > 5 else ""
    body_rows = "".join(
        f'<tr><td class="qty">{_fmt(r.get("count"))}</td>'
        f'<td>{_e(r.get("license_name"))}</td>'
        f'<td class="type">{_e(r.get("license_type"))}</td></tr>'
        for r in rows)
    return _card("NI SW Licenses (Finite Qty)",
                 f'<table class="finite-table{density}"><tr><th>QTY</th>'
                 f'<th>LICENSE</th><th>TYPE</th></tr>{body_rows}</table>')


def _trend_card(data) -> str:
    return _card("Software Usage Trend",
                 _chart_svg(data.get("machine", {}).get("df")))


def _usage_card(data) -> str:
    s = data.get("machine", {}).get("stats", {})
    body = (
        '<div class="stats">'
        f'<div class="stat accent"><div class="big" style="color:{ACCENT}">'
        f'{_fmt(s.get("max_total", 0))}</div>'
        f'<div class="lbl">Peak machines</div>'
        f'<div class="per">{_e(s.get("max_period", "—"))}</div></div>'
        f'<div class="stat"><div class="big" style="color:{DARK}">'
        f'{_fmt(s.get("min_total", 0))}</div>'
        f'<div class="lbl">Min machines</div>'
        f'<div class="per">{_e(s.get("min_period", "—"))}</div></div></div>'
        f'<div class="strip"><span>Avg quarterly increase</span>'
        f'<span class="pct">{s.get("avg_pct_change", 0):+.1f}%</span></div>')
    return _card("Software Usage Data", body)


def _locations_card(data) -> str:
    rows = data.get("locations_top5", []) or []
    if not rows:
        return _card("Top Site Locations", '<div class="empty">No location data</div>')
    body_rows = "".join(
        f'<tr><td>{_e(r.get("state"))}</td>'
        f'<td>{_e(r.get("city") or r.get("location"))}</td>'
        f'<td class="qty" style="text-align:right">{_fmt(r.get("count"))}</td></tr>'
        for r in rows[:5])
    return _card("Top Site Locations",
                 f'<table class="site-table"><tr><th>STATE</th><th>CITY</th>'
                 f'<th style="text-align:right">MACHINES</th></tr>{body_rows}</table>')


def _versions_card(data) -> str:
    rows = data.get("versions_top5", []) or []
    if not rows:
        return _card("Version Usage", '<div class="empty">No version data</div>')
    body_rows = "".join(
        f'<tr><td>{_e(r.get("product"))}</td>'
        f'<td style="text-align:right">{_fmt(r.get("product_total", r.get("users")))}</td>'
        f'<td>{_e(r.get("version"))}</td>'
        f'<td class="qty" style="text-align:right">{int(r.get("pct", 0))}%</td></tr>'
        for r in rows[:5])
    return _card("Version Usage",
                 f'<table class="version-table"><tr><th>PRODUCT</th>'
                 f'<th style="text-align:right">TOTAL</th><th>TOP VER.</th>'
                 f'<th style="text-align:right">%</th></tr>{body_rows}</table>')


def _credits_card(data) -> str:
    c = data.get("credits", {}) or {}
    pct = c.get("pct_used", "—")
    pct_txt = f"{pct}%" if pct not in ("", "—", None) else "—"
    body = ('<div class="stats3">'
            f'<div><div class="lbl">Purchased</div>'
            f'<div class="med" style="color:{DARK}">{_fmt(c.get("purchased", "—"))}</div></div>'
            f'<div><div class="lbl">Used</div>'
            f'<div class="med" style="color:{DARK}">{_fmt(c.get("used", "—"))}</div></div>'
            f'<div><div class="lbl">Utilized</div>'
            f'<div class="med" style="color:{ACCENT}">{_e(pct_txt)}</div></div></div>')
    return _card("Training Credit Usage", body)


def _support_card(data) -> str:
    s = data.get("support", {}) or {}
    return (f'<div class="card dark"><div class="ctitle" style="color:{MUTED}">'
            f'TECHNICAL SUPPORT</div><div class="supp">'
            f'<b>{_e(s.get("tier", "—"))}</b>'
            f'<span class="scope">{_e(s.get("scope", ""))}</span></div></div>')


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def generate_preview_html(data: dict) -> str:
    """Full self-contained HTML preview of the slide."""
    sid = _e(data.get("service_id") or "EA-—")
    cust = _e(data.get("customer") or "Customer")
    updated = _e(data.get("updated_date", ""))

    css = f"""
    <style>
      * {{ box-sizing: border-box; margin: 0; }}
      .slide {{ width: 100%; max-width: 1160px; aspect-ratio: 16/9;
        background: #fff; border: 1px solid {BORDER}; font-family: 'Segoe UI',
        Calibri, Arial, sans-serif; display: flex; flex-direction: column;
        overflow: hidden; }}
      .band {{ background: {DARK}; color: #fff; padding: 10px 26px 12px;
        display: flex; justify-content: space-between; align-items: flex-end; }}
      .band .label {{ font-size: 9px; letter-spacing: 2.5px; color: {MUTED};
        font-weight: 700; }}
      .band h1 {{ font-family: Georgia, serif; font-size: 24px; margin-top: 2px; }}
      .band .upd {{ font-size: 10px; color: {MUTED}; }}
      .cols {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;
        padding: 12px 22px 16px; flex: 1; min-height: 0; }}
      .col {{ display: flex; flex-direction: column; gap: 9px; min-height: 0; }}
      .card {{ background: #fff; border: 1px solid {BORDER}; border-radius: 8px;
        padding: 7px 9px; display: flex; flex-direction: column; min-height: 0;
        overflow: hidden; }}
      .card.grow {{ flex: 1; }}
      .card.dark {{ background: {DARK}; border-color: {DARK}; }}
      .ctitle {{ font-size: 8.5px; letter-spacing: 2px; color: {ACCENT};
        font-weight: 700; text-transform: uppercase; margin-bottom: 5px;
        flex: 0 0 auto; }}
      .card-body {{ flex: 1 1 auto; min-height: 0; overflow: hidden; }}
      .contract-card .card-body {{ display: grid;
        grid-template-rows: repeat(4, minmax(0, 1fr)); }}
      .krow {{ display: flex; justify-content: space-between; font-size: 11px;
        padding: 0; align-items: center; gap: 8px; min-height: 0;
        line-height: 1.08; }}
      .krow .k {{ color: {GRAY}; }}
      .krow .v {{ color: {DARK}; font-weight: 700; text-align: right;
        overflow-wrap: anywhere; }}
      .pill {{ border: 1.5px solid {ACCENT}; border-radius: 7px; padding: 5px;
        text-align: center; font-size: 10.5px; font-weight: 700; color: {DARK};
        margin-bottom: 6px; }}
      table {{ width: 100%; border-collapse: collapse; font-size: 10px; }}
      th {{ background: {DARK}; color: #fff; font-size: 8px; letter-spacing: 1px;
        padding: 4px 6px; text-align: left; }}
      td {{ padding: 4px 6px; color: {DARK}; }}
      tr:nth-child(odd) td {{ background: {TINT}; }}
      .finite-table, .site-table, .version-table {{ table-layout: fixed; }}
      .finite-table th, .finite-table td, .site-table th, .site-table td,
      .version-table th, .version-table td {{
        overflow-wrap: anywhere; line-height: 1.12; }}
      .finite-table th, .finite-table td {{ padding: 3px 4px; }}
      .finite-table th:nth-child(1), .finite-table td:nth-child(1) {{ width: 14%; }}
      .finite-table th:nth-child(2), .finite-table td:nth-child(2) {{ width: 56%; }}
      .finite-table th:nth-child(3), .finite-table td:nth-child(3) {{ width: 30%; }}
      .finite-table.dense {{ font-size: 8px; }}
      .finite-table.ultra-dense {{ font-size: 7px; }}
      .finite-table.dense th, .finite-table.dense td,
      .finite-table.ultra-dense th, .finite-table.ultra-dense td {{ padding: 2px 3px; }}
      .site-table, .version-table {{ height: 100%; }}
      .site-table {{ font-size: 8px; }}
      .site-table th, .site-table td {{ padding: 2px 4px; }}
      .site-table th:nth-child(1), .site-table td:nth-child(1) {{ width: 22%; }}
      .site-table th:nth-child(2), .site-table td:nth-child(2) {{ width: 48%; }}
      .site-table th:nth-child(3), .site-table td:nth-child(3) {{ width: 30%; }}
      .version-table {{ font-size: 7.5px; }}
      .version-table th, .version-table td {{ padding: 2px 3px; }}
      .version-table th:nth-child(1), .version-table td:nth-child(1) {{ width: 38%; }}
      .version-table th:nth-child(2), .version-table td:nth-child(2) {{ width: 19%; }}
      .version-table th:nth-child(3), .version-table td:nth-child(3) {{ width: 27%; }}
      .version-table th:nth-child(4), .version-table td:nth-child(4) {{ width: 16%; }}
      td.qty {{ color: {ACCENT}; font-weight: 700; }}
      td.type {{ color: {GRAY}; font-size: 9px; }}
      .more {{ font-size: 9px; color: {GRAY}; text-align: right; margin-top: 3px; }}
      .empty {{ color: {GRAY}; font-size: 10.5px; text-align: center;
        padding: 14px 0; }}
      .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }}
      .stat {{ border: 1.5px solid {BORDER}; border-radius: 8px; padding: 9px;
        text-align: center; }}
      .stat.accent {{ border-color: {ACCENT}; }}
      .big {{ font-family: Georgia, serif; font-size: 26px; font-weight: 700; }}
      .med {{ font-family: Georgia, serif; font-size: 19px; font-weight: 700; }}
      .lbl {{ font-size: 9px; color: {GRAY}; margin-top: 2px; }}
      .per {{ font-size: 9px; color: {DARK}; }}
      .strip {{ background: {TINT}; border-radius: 6px; margin-top: 9px;
        padding: 7px 11px; display: flex; justify-content: space-between;
        align-items: center; font-size: 11px; color: {DARK}; }}
      .strip .pct {{ font-family: Georgia, serif; font-size: 21px;
        font-weight: 700; color: {ACCENT}; }}
      .stats3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr;
        text-align: center; gap: 5px; }}
      .supp {{ color: #fff; font-size: 12.5px; }}
      .supp .scope {{ color: {MUTED}; font-size: 10.5px; margin-left: 8px; }}
    </style>"""

    left = (_contract_card(data) + _bundles_card(data)
            + _finite_card(data).replace('class="card "', 'class="card grow"'))
    center = (_trend_card(data).replace('class="card "', 'class="card grow"')
              + _usage_card(data))
    right = (_locations_card(data) + _versions_card(data)
             + _credits_card(data) + _support_card(data))

    return f"""{css}
    <div class="slide">
      <div class="band">
        <div>
          <div class="label">ENTERPRISE AGREEMENT</div>
          <h1>{sid} &middot; {cust}</h1>
        </div>
        <div class="upd">Updated {updated}</div>
      </div>
      <div class="cols">
        <div class="col">{left}</div>
        <div class="col">{center}</div>
        <div class="col">{right}</div>
      </div>
    </div>"""
