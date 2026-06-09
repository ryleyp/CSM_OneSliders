"""
Builds a single 16:9 .pptx slide.
Tables are fully dynamic — they expand to fit all rows, font scales to fit.
No network calls.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.chart.data import ChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

# ---------------------------------------------------------------------------
# Theme colours
# ---------------------------------------------------------------------------
DARK_GREEN   = RGBColor(0x01, 0x33, 0x24)
ACCENT_GREEN = RGBColor(0x18, 0xAF, 0x7C)
WHITE        = RGBColor(0xFF, 0xFF, 0xFF)
BLACK        = RGBColor(0x00, 0x00, 0x00)
LIGHT_GREY   = RGBColor(0xF2, 0xF2, 0xF2)

# ---------------------------------------------------------------------------
# Slide dimensions & layout constants
# ---------------------------------------------------------------------------
SLIDE_W = Emu(9144000)   # 10 in
SLIDE_H = Emu(5143500)   # 7.5 in  (16:9)

MARGIN   = Emu(228600)   # 0.25 in
TITLE_H  = Emu(457200)   # 0.5  in
GAP      = Emu(114300)   # 0.125 in

BOX_TOP  = MARGIN + TITLE_H + GAP
BOX_H    = Emu(400000)

COL_TOP    = BOX_TOP + BOX_H + GAP
COL_HEIGHT = SLIDE_H - COL_TOP - MARGIN
COL_W      = Emu((int(SLIDE_W) - int(MARGIN) * 2 - int(GAP) * 2) // 3)

LEFT_X   = MARGIN
CENTER_X = Emu(int(LEFT_X)   + int(COL_W) + int(GAP))
RIGHT_X  = Emu(int(CENTER_X) + int(COL_W) + int(GAP))

# Row heights at each font size (Pt → approximate Emu per row)
def _row_h(font_size: float) -> int:
    return int(Pt(font_size + 3).emu) + 50000


def _auto_font(n_data_rows: int, available_h: int, header_rows: int = 1,
               max_fs: float = 8.0, min_fs: float = 5.5) -> float:
    """Pick the largest font size where all rows fit in available_h."""
    fs = max_fs
    while fs >= min_fs:
        if _row_h(fs) * (n_data_rows + header_rows) <= available_h:
            return fs
        fs -= 0.5
    return min_fs


# ---------------------------------------------------------------------------
# Low-level drawing helpers
# ---------------------------------------------------------------------------

def _textbox(slide, left, top, width, height, text,
             bold=False, size=10, color=BLACK, align=PP_ALIGN.LEFT, bg=None):
    txb = slide.shapes.add_textbox(left, top, width, height)
    if bg:
        txb.fill.solid()
        txb.fill.fore_color.rgb = bg
    tf = txb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.bold  = bold
    run.font.size  = Pt(size)
    run.font.color.rgb = color
    return txb


def _table(slide, left, top, width, rows_data, col_widths, font_size=8.0):
    """
    Draws a table and returns (table_object, bottom_y).
    rows_data[0] is treated as header.
    """
    n_rows = len(rows_data)
    n_cols = len(rows_data[0]) if rows_data else 1
    rh     = _row_h(font_size)
    total_h = rh * n_rows

    tbl_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, total_h)
    tbl = tbl_shape.table

    for ci, cw in enumerate(col_widths):
        tbl.columns[ci].width = cw

    for ri, row_vals in enumerate(rows_data):
        is_header = (ri == 0)
        for ci, val in enumerate(row_vals):
            cell = tbl.cell(ri, ci)
            cell.text = str(val)
            tf   = cell.text_frame
            para = tf.paragraphs[0]
            para.font.size  = Pt(font_size)
            para.font.bold  = is_header
            if is_header:
                para.font.color.rgb = WHITE
                cell.fill.solid()
                cell.fill.fore_color.rgb = DARK_GREEN
            else:
                para.font.color.rgb = BLACK
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT_GREY if ri % 2 == 0 else WHITE

    return tbl, Emu(top + total_h)


def _section_hdr(slide, left, top, width, title: str) -> Emu:
    bar_h = Emu(int(Pt(9).emu) + 80000)
    _textbox(slide, left, top, width, bar_h, title,
             bold=True, size=8, color=WHITE, bg=DARK_GREEN, align=PP_ALIGN.CENTER)
    return Emu(int(top) + int(bar_h))


def _rounded_box(slide, left, top, width, height, text_lines: list[str]):
    shape = slide.shapes.add_shape(5, left, top, width, height)
    try:
        if len(shape.adjustments) > 0:
            shape.adjustments[0] = 0.05
    except Exception:
        pass
    shape.fill.solid()
    shape.fill.fore_color.rgb = WHITE
    shape.line.color.rgb = ACCENT_GREEN
    shape.line.width = Pt(1.5)
    tf = shape.text_frame
    tf.word_wrap = False
    for i, line in enumerate(text_lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = line
        run.font.size  = Pt(8)
        run.font.color.rgb = DARK_GREEN


def _line_chart(slide, left, top, width, height, periods, totals):
    cd = ChartData()
    cd.categories = periods
    cd.add_series("Sessions", totals)
    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.LINE, left, top, width, height, cd
    ).chart
    chart.series[0].format.line.color.rgb = ACCENT_GREEN
    chart.series[0].format.line.width = Pt(2)
    chart.has_legend = False
    try:
        chart.font.size = Pt(7)
    except Exception:
        pass
    for axis_attr in ("category_axis", "value_axis"):
        try:
            getattr(chart, axis_attr).tick_labels.font.size = Pt(6)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_slide(data: dict[str, Any], contract: dict[str, Any], out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE

    # ------------------------------------------------------------------
    # Title
    # ------------------------------------------------------------------
    ea_num   = contract.get("ea_number", "EA-XXXXXX")
    customer = contract.get("customer_name", "Customer")
    _textbox(slide, MARGIN, MARGIN, Emu(int(SLIDE_W) - int(MARGIN) * 2), TITLE_H,
             f"{ea_num} - {customer}", bold=True, size=14, color=DARK_GREEN)

    # ------------------------------------------------------------------
    # EA Info Box
    # ------------------------------------------------------------------
    _rounded_box(slide, MARGIN, BOX_TOP, Emu(int(SLIDE_W) - int(MARGIN) * 2), BOX_H, [
        f"EA End Date: {contract.get('ea_end_date','N/A')}     "
        f"Term: {contract.get('term_duration','N/A')}     "
        f"Scope: {contract.get('contract_scope','N/A')}     "
        f"Phase: {contract.get('phase','N/A')}"
    ])

    # ==================================================================
    # LEFT COLUMN — Bundle Info + Finite Quantity Licenses
    # ==================================================================
    y = COL_TOP
    bundles = contract.get("bundles", [])
    fql     = contract.get("finite_quantity_licenses", [])

    # Decide how much vertical space each table gets
    # Bundle table is typically small; licenses get the rest
    hdr_h      = Emu(int(Pt(9).emu) + 80000)
    row_reserve = _row_h(7.5)

    b_data_rows = max(1, len(bundles))
    l_data_rows = max(1, len(fql))

    # Fixed: bundle header + rows, then licenses fill remaining space
    bundle_block_h = int(hdr_h) + _row_h(7.5) * (b_data_rows + 1)  # +1 for header row
    lic_avail_h    = int(COL_HEIGHT) - bundle_block_h - int(GAP) * 2

    # Auto-size license font to fit all rows
    lic_fs = _auto_font(l_data_rows, lic_avail_h, header_rows=1, max_fs=8.0, min_fs=5.0)

    # --- Bundle table ---
    y = _section_hdr(slide, LEFT_X, y, COL_W, "Bundle Information")
    b_rows = [["Bundle Name", "Type"]]
    for b in bundles:
        b_rows.append([b.get("name", ""), b.get("type", "")])
    if not bundles:
        b_rows.append(["No bundles defined", ""])
    cw_b = [int(COL_W * 0.65), int(COL_W * 0.35)]
    _, y = _table(slide, LEFT_X, y, COL_W, b_rows, cw_b, font_size=7.5)
    y = Emu(int(y) + int(GAP))

    # --- License table ---
    y = _section_hdr(slide, LEFT_X, y, COL_W, "Finite Quantity Licenses")
    l_rows = [["Qty", "Product", "Type"]]
    for lic in fql:
        l_rows.append([str(lic.get("count", "")), lic.get("name", ""), lic.get("type", "")])
    if not fql:
        l_rows.append(["—", "No licenses defined", ""])
    cw_l = [int(COL_W * 0.14), int(COL_W * 0.54), int(COL_W * 0.32)]
    _table(slide, LEFT_X, y, COL_W, l_rows, cw_l, font_size=lic_fs)

    # ==================================================================
    # CENTER COLUMN — Trend chart + Usage summary table
    # ==================================================================
    yc       = COL_TOP
    machines = data.get("machines")

    yc = _section_hdr(slide, CENTER_X, yc, COL_W, "Software Usage Trend")
    chart_h = Emu(int(COL_HEIGHT * 0.50))

    if machines and len(machines["periods"]) >= 2:
        _line_chart(slide, CENTER_X, yc, COL_W, chart_h,
                    machines["periods"], machines["totals"])
    else:
        _textbox(slide, CENTER_X, yc, COL_W, chart_h,
                 "Insufficient period data for trend chart\n"
                 "(need ≥2 quarters/months)", size=7, color=BLACK)
    yc = Emu(int(yc) + int(chart_h) + int(GAP))

    yc = _section_hdr(slide, CENTER_X, yc, COL_W, "Software Usage Data")
    if machines:
        max_s = f"{machines['max_sessions']:,} ({machines['max_period']})"
        min_s = f"{machines['min_sessions']:,} ({machines['min_period']})"
        avg_c = f"{machines['avg_pct_change']:+.1f}%"
    else:
        max_s = min_s = avg_c = "N/A"

    usage_rows = [
        ["Metric", "Value"],
        ["Peak Sessions", max_s],
        ["Low Sessions",  min_s],
        ["Avg QoQ Change", avg_c],
    ]
    cw_u = [int(COL_W * 0.50), int(COL_W * 0.50)]
    _, yc = _table(slide, CENTER_X, yc, COL_W, usage_rows, cw_u, font_size=7.5)

    # ==================================================================
    # RIGHT COLUMN — Locations | Version Usage | Training Credits | Support
    # ==================================================================
    yr = COL_TOP

    # --- Top Site Locations ---
    yr = _section_hdr(slide, RIGHT_X, yr, COL_W, "Top Site Locations")
    cities = data.get("cities")
    if cities and cities["top_locations"]:
        loc_rows = [["Location", "Sessions", "%"]]
        for loc in cities["top_locations"]:
            loc_rows.append([loc["label"], f"{loc['usage']:,}", f"{loc['pct_of_total']}%"])
    else:
        loc_rows = [["Location", "Sessions", "%"], ["No data", "—", "—"]]
    cw_loc = [int(COL_W * 0.50), int(COL_W * 0.28), int(COL_W * 0.22)]
    _, yr = _table(slide, RIGHT_X, yr, COL_W, loc_rows, cw_loc, font_size=7.5)
    yr = Emu(int(yr) + int(GAP))

    # --- Version Usage ---
    yr = _section_hdr(slide, RIGHT_X, yr, COL_W, "Version Usage")
    software = data.get("software")
    if software and software["products"]:
        ver_rows = [["Product", "Top Version", "Usage"]]
        for p in software["products"]:
            ver_rows.append([p["product"][:20], p["top_version"][:12], f"{p['usage']:,}"])
    else:
        ver_rows = [["Product", "Top Version", "Usage"], ["No data", "—", "—"]]

    # Auto-size to fit remaining right-column height
    ver_avail  = int(COL_HEIGHT) - (int(yr) - int(COL_TOP)) - int(GAP) * 2 - 300000
    ver_fs = _auto_font(len(ver_rows) - 1, ver_avail // 2, max_fs=7.5, min_fs=5.0)
    cw_ver = [int(COL_W * 0.42), int(COL_W * 0.30), int(COL_W * 0.28)]
    _, yr = _table(slide, RIGHT_X, yr, COL_W, ver_rows, cw_ver, font_size=ver_fs)
    yr = Emu(int(yr) + int(GAP))

    # --- Training Credits ---
    yr = _section_hdr(slide, RIGHT_X, yr, COL_W, "Training Credit Usage")
    tc_total = int(contract.get("training_credits_total") or 0)
    tc_used  = int(contract.get("training_credits_used")  or 0)
    tc_rem   = int(contract.get("training_credits_remaining") or max(0, tc_total - tc_used))
    tc_pct   = f"{round(tc_used / tc_total * 100, 1)}%" if tc_total else "N/A"
    tc_rows  = [
        ["Metric", "Value"],
        ["Total",     str(tc_total) if tc_total else "N/A"],
        ["Used",      str(tc_used)  if tc_total else "N/A"],
        ["Remaining", str(tc_rem)   if tc_total else "N/A"],
        ["% Used",    tc_pct],
    ]
    cw_tc = [int(COL_W * 0.55), int(COL_W * 0.45)]
    _, yr = _table(slide, RIGHT_X, yr, COL_W, tc_rows, cw_tc, font_size=7.5)
    yr = Emu(int(yr) + int(GAP))

    # --- Technical Support ---
    yr = _section_hdr(slide, RIGHT_X, yr, COL_W, "Technical Support")
    ts_rows = [["Support Level"], [contract.get("technical_support_level", "Standard")]]
    _table(slide, RIGHT_X, yr, COL_W, ts_rows, [COL_W], font_size=7.5)

    prs.save(out_path)
    return out_path
