"""
Builds a single 16:9 .pptx slide with the EA account summary layout.
No network calls. Uses python-pptx only.

Layout (all in EMU coordinates, slide = 9144000 x 5143500):

  [Title]
  [EA Info Rounded Box]
  Left col  : Bundle Info table + Finite Qty Licenses table
  Center col: Software Usage Trend chart + Usage Data table
  Right col : Top Sites | Version Usage | Training Credits | Tech Support
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.chart.data import ChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Cm, Emu, Inches, Pt

# ---------------------------------------------------------------------------
# Theme colours
# ---------------------------------------------------------------------------
DARK_GREEN  = RGBColor(0x01, 0x33, 0x24)   # #013324
ACCENT_GREEN = RGBColor(0x18, 0xAF, 0x7C)  # #18af7c
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
BLACK       = RGBColor(0x00, 0x00, 0x00)
LIGHT_GREY  = RGBColor(0xF2, 0xF2, 0xF2)

# ---------------------------------------------------------------------------
# Slide dimensions (16:9)
# ---------------------------------------------------------------------------
SLIDE_W = Emu(9144000)
SLIDE_H = Emu(5143500)

# Layout constants (in Emu)
MARGIN    = Emu(228600)   # ~0.25 in
TITLE_H   = Emu(457200)   # ~0.5 in
BOX_H     = Emu(457200)
BOX_TOP   = MARGIN + TITLE_H + Emu(114300)

# Three-column layout starts below the box
COL_TOP    = BOX_TOP + BOX_H + Emu(114300)
COL_HEIGHT = SLIDE_H - COL_TOP - MARGIN
COL_W      = Emu((9144000 - MARGIN * 2 - Emu(114300) * 2) // 3)

LEFT_X   = MARGIN
CENTER_X = LEFT_X + COL_W + Emu(114300)
RIGHT_X  = CENTER_X + COL_W + Emu(114300)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _rgb(r: int, g: int, b: int) -> RGBColor:
    return RGBColor(r, g, b)


def _add_textbox(slide, left, top, width, height, text,
                 bold=False, size=10, color=BLACK, align=PP_ALIGN.LEFT,
                 bg_color=None):
    txb = slide.shapes.add_textbox(left, top, width, height)
    if bg_color:
        fill = txb.fill
        fill.solid()
        fill.fore_color.rgb = bg_color
    tf = txb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.bold = bold
    run.font.size = Pt(size)
    run.font.color.rgb = color
    return txb


def _add_table(slide, left, top, width, rows_data, col_widths,
               header_bg=DARK_GREEN, header_fg=WHITE,
               row_bg=WHITE, row_fg=BLACK,
               alt_row_bg=LIGHT_GREY,
               font_size=8):
    """
    rows_data: list of lists. First row is the header.
    col_widths: list of Emu values (must sum to ~width).
    Returns the table shape.
    """
    n_rows = len(rows_data)
    n_cols = len(rows_data[0]) if rows_data else 1

    # Estimate row height
    row_h = Emu(int(Pt(font_size + 4).emu) + 60000)
    total_h = row_h * n_rows

    tbl = slide.shapes.add_table(n_rows, n_cols, left, top, width, total_h).table

    # Column widths
    for ci, cw in enumerate(col_widths):
        tbl.columns[ci].width = cw

    for ri, row_vals in enumerate(rows_data):
        for ci, val in enumerate(row_vals):
            cell = tbl.cell(ri, ci)
            cell.text = str(val)
            tf = cell.text_frame
            tf.paragraphs[0].font.size = Pt(font_size)
            tf.paragraphs[0].font.bold = (ri == 0)

            if ri == 0:
                tf.paragraphs[0].font.color.rgb = header_fg
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_bg
            else:
                tf.paragraphs[0].font.color.rgb = row_fg
                cell.fill.solid()
                cell.fill.fore_color.rgb = alt_row_bg if ri % 2 == 0 else row_bg

    return tbl, top + total_h


def _add_rounded_box(slide, left, top, width, height, text_lines: list[str]):
    """Rounded rectangle with ACCENT_GREEN border, white fill, multiline text."""
    from pptx.util import Emu as _Emu
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    # MSO_SHAPE_TYPE enum value for rounded rectangle is 5 in pptx
    shape = slide.shapes.add_shape(
        5,   # MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE
        left, top, width, height,
    )
    # Rounded rectangle has one adjustment handle; set it if available
    try:
        if len(shape.adjustments) > 0:
            shape.adjustments[0] = 0.05
    except Exception:
        pass

    fill = shape.fill
    fill.solid()
    fill.fore_color.rgb = WHITE

    line = shape.line
    line.color.rgb = ACCENT_GREEN
    line.width = Pt(1.5)

    tf = shape.text_frame
    tf.word_wrap = False

    for i, line_text in enumerate(text_lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = line_text
        run.font.size = Pt(8)
        run.font.color.rgb = DARK_GREEN

    return shape


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------

def _section_header(slide, left, top, width, title: str) -> Emu:
    """Adds a dark-green header bar and returns the next Y position."""
    bar_h = Emu(int(Pt(10).emu) + 80000)
    _add_textbox(slide, left, top, width, bar_h, title,
                 bold=True, size=8, color=WHITE, bg_color=DARK_GREEN,
                 align=PP_ALIGN.CENTER)
    return top + bar_h


def _add_line_chart(slide, left, top, width, height,
                    periods: list[str], totals: list[float]) -> None:
    chart_data = ChartData()
    chart_data.categories = periods
    chart_data.add_series("Sessions", totals)

    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.LINE,
        left, top, width, height,
        chart_data,
    ).chart

    # Style the line
    series = chart.series[0]
    series.format.line.color.rgb = ACCENT_GREEN
    series.format.line.width = Pt(2)

    # Font sizes
    try:
        chart.font.size = Pt(7)
    except Exception:
        pass
    chart.has_legend = False

    try:
        cat_axis = chart.category_axis
        cat_axis.tick_labels.font.size = Pt(6)
    except Exception:
        pass

    try:
        val_axis = chart.value_axis
        val_axis.tick_labels.font.size = Pt(6)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main slide builder
# ---------------------------------------------------------------------------

def build_slide(
    data: dict[str, Any],
    contract: dict[str, Any],
    out_path: str | Path,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    blank_layout = prs.slide_layouts[6]   # completely blank
    slide = prs.slides.add_slide(blank_layout)

    # White background
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = WHITE

    # ------------------------------------------------------------------
    # Title
    # ------------------------------------------------------------------
    ea_num   = contract.get("ea_number", "EA-XXXXXX")
    customer = contract.get("customer_name", "Customer")
    title_text = f"{ea_num} - {customer}"

    _add_textbox(
        slide,
        MARGIN, MARGIN,
        SLIDE_W - MARGIN * 2, TITLE_H,
        title_text,
        bold=True, size=14, color=DARK_GREEN,
    )

    # ------------------------------------------------------------------
    # EA Info Rounded Box
    # ------------------------------------------------------------------
    end_date = contract.get("ea_end_date", "N/A")
    term     = contract.get("term_duration", "N/A")
    scope    = contract.get("contract_scope", "N/A")
    phase    = contract.get("phase", "N/A")

    box_text_lines = [
        f"EA End Date: {end_date}     Term: {term}     Scope: {scope}     Phase: {phase}"
    ]
    _add_rounded_box(
        slide,
        MARGIN, BOX_TOP,
        SLIDE_W - MARGIN * 2, BOX_H,
        box_text_lines,
    )

    # ==================================================================
    # LEFT COLUMN
    # ==================================================================
    y = COL_TOP

    # --- Bundle Information ---
    y = _section_header(slide, LEFT_X, y, COL_W, "Bundle Information")
    bundles = contract.get("bundles", [])
    bundle_rows = [["Bundle Name", "Type"]]
    for b in bundles:
        bundle_rows.append([b.get("name", ""), b.get("type", "")])
    if not bundles:
        bundle_rows.append(["No bundles defined", ""])

    cw = [int(COL_W * 0.65), int(COL_W * 0.35)]
    _, y = _add_table(slide, LEFT_X, y, COL_W, bundle_rows, cw)
    y += Emu(100000)

    # --- Finite Quantity Licenses ---
    y = _section_header(slide, LEFT_X, y, COL_W, "Finite Quantity Licenses")
    fql = contract.get("finite_quantity_licenses", [])
    fql_rows = [["Qty", "Product", "Type"]]
    for lic in fql:
        fql_rows.append([
            str(lic.get("count", "")),
            lic.get("name", ""),
            lic.get("type", ""),
        ])
    if not fql:
        fql_rows.append(["—", "No licenses defined", ""])

    cw2 = [int(COL_W * 0.15), int(COL_W * 0.55), int(COL_W * 0.30)]
    _, y = _add_table(slide, LEFT_X, y, COL_W, fql_rows, cw2)

    # ==================================================================
    # CENTER COLUMN
    # ==================================================================
    y_center = COL_TOP
    machines = data.get("machines")

    # --- Software Usage Trend (line chart) ---
    y_center = _section_header(slide, CENTER_X, y_center, COL_W, "Software Usage Trend")

    chart_h = Emu(int(COL_HEIGHT * 0.45))
    if machines and len(machines["periods"]) >= 2:
        _add_line_chart(
            slide,
            CENTER_X, y_center, COL_W, chart_h,
            machines["periods"], [float(t) for t in machines["totals"]],
        )
    else:
        _add_textbox(slide, CENTER_X, y_center, COL_W, chart_h,
                     "Insufficient data for trend chart",
                     size=8, color=BLACK)
    y_center += chart_h + Emu(80000)

    # --- Software Usage Data table ---
    y_center = _section_header(slide, CENTER_X, y_center, COL_W, "Software Usage Data")

    max_s = f"{machines['max_sessions']:,} ({machines['max_period']})" if machines else "N/A"
    min_s = f"{machines['min_sessions']:,} ({machines['min_period']})" if machines else "N/A"
    avg_c = f"{machines['avg_pct_change']:+.1f}%" if machines else "N/A"

    usage_rows = [
        ["Metric", "Value"],
        ["Max Sessions", max_s],
        ["Min Sessions", min_s],
        ["Avg QoQ Change", avg_c],
    ]
    cw3 = [int(COL_W * 0.50), int(COL_W * 0.50)]
    _, y_center = _add_table(slide, CENTER_X, y_center, COL_W, usage_rows, cw3)

    # ==================================================================
    # RIGHT COLUMN
    # ==================================================================
    y_right = COL_TOP

    # --- Top Site Locations ---
    y_right = _section_header(slide, RIGHT_X, y_right, COL_W, "Top Site Locations")
    cities = data.get("cities")
    if cities and cities["top_locations"]:
        loc_rows = [["Location", "Sessions", "%"]]
        for loc in cities["top_locations"]:
            loc_rows.append([loc["label"], f"{loc['usage']:,}", f"{loc['pct_of_total']}%"])
    else:
        loc_rows = [["Location", "Sessions", "%"], ["No data", "—", "—"]]

    cw4 = [int(COL_W * 0.50), int(COL_W * 0.28), int(COL_W * 0.22)]
    _, y_right = _add_table(slide, RIGHT_X, y_right, COL_W, loc_rows, cw4)
    y_right += Emu(80000)

    # --- Version Usage ---
    y_right = _section_header(slide, RIGHT_X, y_right, COL_W, "Version Usage")
    software = data.get("software")
    if software and software["products"]:
        ver_rows = [["Product", "Top Version", "Usage"]]
        for p in software["products"][:6]:
            ver_rows.append([
                p["product"][:18],
                p["top_version"][:12],
                f"{p['usage']:,}",
            ])
    else:
        ver_rows = [["Product", "Top Version", "Usage"], ["No data", "—", "—"]]

    cw5 = [int(COL_W * 0.40), int(COL_W * 0.30), int(COL_W * 0.30)]
    _, y_right = _add_table(slide, RIGHT_X, y_right, COL_W, ver_rows, cw5)
    y_right += Emu(80000)

    # --- Training Credit Usage ---
    y_right = _section_header(slide, RIGHT_X, y_right, COL_W, "Training Credit Usage")
    tc_total = int(contract.get("training_credits_total") or 0)
    tc_used  = int(contract.get("training_credits_used") or 0)
    tc_rem   = tc_total - tc_used
    tc_pct   = f"{round(tc_used / tc_total * 100, 1)}%" if tc_total else "N/A"

    tc_rows = [
        ["Metric", "Value"],
        ["Total Credits", str(tc_total) if tc_total else "N/A"],
        ["Used",          str(tc_used)  if tc_total else "N/A"],
        ["Remaining",     str(tc_rem)   if tc_total else "N/A"],
        ["% Used",        tc_pct],
    ]
    cw6 = [int(COL_W * 0.55), int(COL_W * 0.45)]
    _, y_right = _add_table(slide, RIGHT_X, y_right, COL_W, tc_rows, cw6)
    y_right += Emu(80000)

    # --- Technical Support ---
    y_right = _section_header(slide, RIGHT_X, y_right, COL_W, "Technical Support")
    support_level = contract.get("technical_support_level", "Standard")
    ts_rows = [
        ["Support Level"],
        [support_level],
    ]
    cw7 = [COL_W]
    _, y_right = _add_table(slide, RIGHT_X, y_right, COL_W, ts_rows, cw7)

    # ------------------------------------------------------------------
    prs.save(out_path)
    return out_path
