"""app.py — ea-slide-builder (Streamlit UI)

A single-page, local-only tool that turns pasted Excel tables + three contract
screenshots into a polished 16:9 EA one-slider (.pptx) plus on-page CSM insights.

Runs entirely on the user's PC. No outbound network calls, no telemetry (see
.streamlit/config.toml). Teammates reach it over the LAN at
http://<your-PC-ip>:8501 while the app is running.

Flow (top to bottom):
  PART 1 — paste three tab-separated tables (machine count, locations, versions)
  PART 2 — upload three screenshots; OCR fills EDITABLE fields the user reviews
  PART 3 — Generate Slide: download the .pptx and read the CSM insights
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import data_processor as dp
import screenshot_reader as sr
from insights import generate_insights
from slide_builder import build_slide

st.set_page_config(page_title="EA Slide Builder", page_icon="📊",
                   layout="wide")

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("📊 EA Slide Builder")
st.caption(
    "Runs **fully offline** on this PC — no internet, no telemetry, no external "
    "APIs. Paste your tables, upload the three screenshots, review every parsed "
    "value, then generate the one-slider."
)


def _file_id(uploaded) -> str | None:
    """Stable id for an uploaded file so we only re-OCR when it changes."""
    if uploaded is None:
        return None
    return f"{uploaded.name}:{uploaded.size}"


# =========================================================================== #
# PART 1 — Paste tables
# =========================================================================== #
st.header("Part 1 · Paste tables")
st.write("Copy each table from Excel (tab-separated) and paste it below.")

c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("1. Machine Count")
    st.caption("Paste the BI export with columns: **Year · Quarter · Month · "
               "Machine Type · Distinct count**  \n"
               "e.g. `2025⇥Q1⇥March⇥Existing⇥711`  \n"
               "Rolled up to quarterly totals automatically. (A simple "
               "`Period · New · Existing` table also works.)")
    machine_text = st.text_area("Machine count table", height=180,
                                key="machine_text", label_visibility="collapsed")

with c2:
    st.subheader("2. Locations")
    st.caption("Columns: **Location · Machines**  \n"
               "e.g. `Austin, TX⇥320`")
    locations_text = st.text_area("Locations table", height=180,
                                  key="locations_text",
                                  label_visibility="collapsed")

with c3:
    st.subheader("3. Usage Versions")
    st.caption("Columns: **Product · Version · Users**  \n"
               "e.g. `LabVIEW⇥2024 Q3⇥540`")
    versions_text = st.text_area("Usage versions table", height=180,
                                 key="versions_text",
                                 label_visibility="collapsed")

# Live previews so the user can confirm parsing before generating.
machine_df = dp.parse_machine_count(machine_text)
locations_df = dp.parse_locations(locations_text)
versions_df = dp.parse_usage_versions(versions_text)

with st.expander("Preview parsed tables", expanded=False):
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        st.write("**Machine count**")
        st.dataframe(machine_df, use_container_width=True, hide_index=True)
    with pc2:
        st.write("**Locations**")
        st.dataframe(locations_df, use_container_width=True, hide_index=True)
    with pc3:
        st.write("**Usage versions**")
        st.dataframe(versions_df, use_container_width=True, hide_index=True)

# =========================================================================== #
# PART 2 — Upload screenshots (OCR -> editable review fields)
# =========================================================================== #
st.header("Part 2 · Upload screenshots")
st.warning("OCR is imperfect. **Every** value below is editable — review and "
           "correct everything before generating.")

up1, up2, up3 = st.columns(3)
with up1:
    img_a = st.file_uploader("Screenshot A — Contract details",
                             type=["png", "jpg", "jpeg", "bmp", "tiff"])
with up2:
    img_b = st.file_uploader("Screenshot B — Finite licenses",
                             type=["png", "jpg", "jpeg", "bmp", "tiff"])
with up3:
    img_c = st.file_uploader("Screenshot C — Unlimited bundles",
                             type=["png", "jpg", "jpeg", "bmp", "tiff"])


def _ocr_once(uploaded, state_key: str) -> str:
    """OCR an upload once and cache the raw text, re-running only on change."""
    fid = _file_id(uploaded)
    if fid is None:
        return st.session_state.get(state_key + "_text", "")
    if st.session_state.get(state_key + "_fid") != fid:
        try:
            text = sr.ocr_image(uploaded)
        except RuntimeError as exc:
            st.error(str(exc))
            text = ""
        st.session_state[state_key + "_text"] = text
        st.session_state[state_key + "_fid"] = fid
        st.session_state[state_key + "_new"] = True
    return st.session_state.get(state_key + "_text", "")


# --- Screenshot A: Contract details ---------------------------------------- #
st.subheader("Screenshot A · Contract details")
text_a = _ocr_once(img_a, "a")
if st.session_state.pop("a_new", False):
    parsed = sr.parse_contract_details(text_a)
    # Seed editable widget state (only when a new file was OCR'd).
    st.session_state["f_service_id"] = parsed["service_id"]
    st.session_state["f_customer"] = parsed["customer"]
    st.session_state["f_start_date"] = parsed["start_date"]
    st.session_state["f_ep_term"] = parsed["ep_term"]
    st.session_state["f_flex_purchased"] = parsed["flex_credits"]
    st.session_state["f_support_tier"] = parsed["support_level"]
    st.session_state["f_debug"] = parsed["debug_licenses"] or "No"
    # Compute suggested End Date + Phase from Start Date + EP Term.
    start = dp.parse_date(parsed["start_date"])
    term = dp.parse_term_years(parsed["ep_term"])
    end = dp.compute_end_date(start, term)
    ph = dp.compute_phase(start, term)
    st.session_state["f_end_date"] = end.strftime("%d-%b-%Y").upper() if end else ""
    st.session_state["f_phase"] = ph["phase"]
    st.session_state["f_phase_hint"] = ph["hint"]

fa1, fa2 = st.columns(2)
with fa1:
    st.text_input("EA/EP Service ID", key="f_service_id",
                  placeholder="EA-15725")
    st.text_input("Customer / Company", key="f_customer",
                  placeholder="RTX Corporation")
    st.text_input("Start / Effective Date", key="f_start_date",
                  placeholder="02-JAN-2026")
    st.text_input("EP Term", key="f_ep_term", placeholder="3 years")
with fa2:
    cols_e = st.columns([3, 1])
    with cols_e[0]:
        st.text_input("EA End Date (computed — editable)", key="f_end_date",
                      placeholder="01-JAN-2029")
    with cols_e[1]:
        st.write("")
        st.write("")
        if st.button("↻ Recompute", help="Recompute End Date & Phase from the "
                     "current Start Date + EP Term"):
            start = dp.parse_date(st.session_state.get("f_start_date", ""))
            term = dp.parse_term_years(st.session_state.get("f_ep_term", ""))
            end = dp.compute_end_date(start, term)
            ph = dp.compute_phase(start, term)
            if end:
                st.session_state["f_end_date"] = end.strftime("%d-%b-%Y").upper()
            st.session_state["f_phase"] = ph["phase"]
            st.session_state["f_phase_hint"] = ph["hint"]
            st.rerun()
    st.text_input("Phase (computed — editable)", key="f_phase",
                  placeholder="Second Half")
    hint = st.session_state.get("f_phase_hint", "")
    if hint:
        st.caption(f"Hint: **{hint}**")
    st.text_input("Contract Scope (fill in — usually missing)",
                  key="f_contract_scope", placeholder="e.g. All NI software")
    st.selectbox("Debug licenses included", ["Yes", "No"], key="f_debug")

st.markdown("**Technical support**")
sc1, sc2 = st.columns(2)
with sc1:
    st.text_input("Support tier", key="f_support_tier",
                  placeholder="Enterprise Support")
with sc2:
    st.text_input("Support scope", key="f_support_scope",
                  placeholder="All Users")

st.markdown("**Training / FLEX credits**")
tc1, tc2, tc3 = st.columns(3)
with tc1:
    st.text_input("FLEX credits purchased", key="f_flex_purchased",
                  placeholder="20,000")
with tc2:
    st.text_input("Credits used (required)", key="f_flex_used",
                  placeholder="e.g. 7,500")
with tc3:
    purchased_n = dp._to_number(st.session_state.get("f_flex_purchased", ""))
    used_n = dp._to_number(st.session_state.get("f_flex_used", ""))
    if purchased_n and used_n is not None and purchased_n > 0:
        st.metric("% Used", f"{used_n / purchased_n * 100:.0f}%")
    else:
        st.caption("Enter purchased + used to see % used.")

with st.expander("Raw OCR text — Screenshot A"):
    st.text(text_a or "(no text yet)")

# --- Screenshot B: Finite licenses ----------------------------------------- #
st.subheader("Screenshot B · Finite licenses")
text_b = _ocr_once(img_b, "b")
if st.session_state.pop("b_new", False):
    rows = sr.parse_finite_licenses(text_b)
    st.session_state["finite_seed"] = pd.DataFrame(
        rows or [], columns=["count", "license_type", "license_name"]
    )
if "finite_seed" not in st.session_state:
    st.session_state["finite_seed"] = pd.DataFrame(
        columns=["count", "license_type", "license_name"]
    )
st.caption("Columns: count · license type · license name. Edit/add/remove rows.")
finite_edit = st.data_editor(
    st.session_state["finite_seed"], num_rows="dynamic", key="finite_editor",
    use_container_width=True,
    column_config={
        "count": st.column_config.NumberColumn("Count", min_value=0, step=1),
        "license_type": st.column_config.TextColumn("License Type"),
        "license_name": st.column_config.TextColumn("License Name"),
    },
)
with st.expander("Raw OCR text — Screenshot B"):
    st.text(text_b or "(no text yet)")

# --- Screenshot C: Unlimited bundles --------------------------------------- #
st.subheader("Screenshot C · Unlimited bundles")
text_c = _ocr_once(img_c, "c")
if st.session_state.pop("c_new", False):
    bundles = sr.parse_unlimited_bundles(text_c)
    st.session_state["bundle_seed"] = pd.DataFrame(
        {"bundle_name": bundles or []}
    )
if "bundle_seed" not in st.session_state:
    st.session_state["bundle_seed"] = pd.DataFrame({"bundle_name": []})
st.caption("One bundle name per row (the name after the colon). Edit/add/remove.")
bundle_edit = st.data_editor(
    st.session_state["bundle_seed"], num_rows="dynamic", key="bundle_editor",
    use_container_width=True,
    column_config={"bundle_name": st.column_config.TextColumn("Bundle Name")},
)
with st.expander("Raw OCR text — Screenshot C"):
    st.text(text_c or "(no text yet)")

# =========================================================================== #
# PART 3 — Generate
# =========================================================================== #
st.header("Part 3 · Generate slide")


def _collect_data() -> dict:
    """Assemble the reviewed values + computed results into the slide payload."""
    stats = dp.compute_machine_stats(machine_df)

    locations_top5 = dp.top_locations(locations_df, 5)
    versions_top5 = dp.top_versions(versions_df, 5)

    finite = [
        {
            "count": int(r["count"]) if pd.notna(r.get("count")) else 0,
            "license_type": str(r.get("license_type") or "").strip(),
            "license_name": str(r.get("license_name") or "").strip(),
        }
        for _, r in finite_edit.iterrows()
        if str(r.get("license_name") or r.get("license_type") or "").strip()
    ]

    bundles = [
        str(r["bundle_name"]).strip()
        for _, r in bundle_edit.iterrows()
        if str(r.get("bundle_name") or "").strip()
    ]

    purchased_n = dp._to_number(st.session_state.get("f_flex_purchased", ""))
    used_n = dp._to_number(st.session_state.get("f_flex_used", ""))
    pct_used = ""
    if purchased_n and used_n is not None and purchased_n > 0:
        pct_used = round(used_n / purchased_n * 100.0)

    return {
        "service_id": st.session_state.get("f_service_id", ""),
        "customer": st.session_state.get("f_customer", ""),
        "updated_date": date.today().strftime("%d-%b-%Y"),
        "ea_end_date": st.session_state.get("f_end_date", ""),
        "ep_term": st.session_state.get("f_ep_term", ""),
        "contract_scope": st.session_state.get("f_contract_scope", ""),
        "phase": st.session_state.get("f_phase", ""),
        "debug_licenses": st.session_state.get("f_debug", ""),
        "bundles": bundles,
        "finite_licenses": finite,
        "machine": {"df": machine_df, "stats": stats},
        "locations_top5": locations_top5,
        "versions_top5": versions_top5,
        "credits": {
            "purchased": st.session_state.get("f_flex_purchased", "") or "—",
            "used": st.session_state.get("f_flex_used", "") or "—",
            "pct_used": pct_used if pct_used != "" else "—",
        },
        "support": {
            "tier": st.session_state.get("f_support_tier", "") or "—",
            "scope": st.session_state.get("f_support_scope", ""),
        },
    }


generate = st.button("🛠️ Generate Slide", type="primary",
                     use_container_width=True)

if generate:
    # Light validation: credits used is a required field per spec.
    used_n = dp._to_number(st.session_state.get("f_flex_used", ""))
    if used_n is None:
        st.error("Credits **used** is required — enter it under Training / FLEX "
                 "credits before generating.")
    elif machine_df.empty:
        st.error("No machine-count data parsed — paste the Machine Count table "
                 "in Part 1.")
    else:
        data = _collect_data()
        try:
            pptx_buf = build_slide(data)
        except Exception as exc:  # surface build errors instead of crashing
            st.exception(exc)
            st.stop()

        st.success("Slide generated.")
        fname = f"{data['service_id'] or 'EA'}_{data['customer'] or 'customer'}"
        fname = fname.replace(" ", "_").replace("/", "-") + ".pptx"
        st.download_button(
            "⬇️ Download .pptx", data=pptx_buf, file_name=fname,
            mime=("application/vnd.openxmlformats-officedocument."
                  "presentationml.presentation"),
            use_container_width=True,
        )

        # On-page slide preview of the trend.
        st.subheader("Machine count trend (preview)")
        st.line_chart(machine_df.set_index("period")["total"])

        # ----------------------------------------------------------------- #
        # CSM insights (pure local computation)
        # ----------------------------------------------------------------- #
        st.subheader("🧠 CSM Insights")
        st.caption("Computed locally from your data — no LLM, no network.")
        items = generate_insights(data)
        if not items:
            st.info("Not enough data to generate insights yet.")
        for it in items:
            urgency = {1: "🔴", 2: "🟠", 3: "🟢", 4: "🔵"}.get(it["priority"], "•")
            st.markdown(f"{urgency} **{it['category']}** — {it['text']}")
