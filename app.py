"""app.py — ea-slide-builder (Streamlit UI)

A single-page, local-only tool that turns pasted BI tables + three contract
screenshots into a polished 16:9 EA one-slider (.pptx) plus on-page CSM
insights.

Runs entirely on the user's PC. No outbound network calls, no telemetry (see
.streamlit/config.toml). Bound to localhost by default — private to this
machine.

Flow (top to bottom):
  Profiles — save/load everything entered for an account; batch-generate decks
  PART 1  — paste three tab-separated tables (machine count, locations, versions)
  PART 2  — upload screenshots; OCR fills EDITABLE fields the user reviews
  PART 3  — Generate: on-page preview, .pptx download, CSM insights
"""

from __future__ import annotations

import platform
import shutil
import sys
from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import data_processor as dp
import profiles as prof
import screenshot_reader as sr
from insights import generate_insights
from preview import generate_preview_html
from slide_builder import build_deck, build_slide
from slide_preview import preview_renderer_status, render_pptx_preview

st.set_page_config(page_title="EA Slide Builder", page_icon="📊",
                   layout="wide")

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("📊 EA Slide Builder")
st.caption(
    "Runs **fully offline** on this PC — no internet, no telemetry, no external "
    "APIs. Paste your tables, upload the screenshots, review every parsed "
    "value, then generate the one-slider."
)


def _file_id(uploaded) -> str | None:
    """Stable id for an uploaded file so we only re-OCR when it changes."""
    if uploaded is None:
        return None
    return f"{uploaded.name}:{uploaded.size}"


def _editor_nonce() -> int:
    return st.session_state.setdefault("editor_nonce", 0)


def _bump_editor_nonce() -> None:
    """Change the data_editor keys so they reload their seed DataFrames."""
    st.session_state["editor_nonce"] = _editor_nonce() + 1


SAMPLE_MACHINE_TEXT = "\n".join([
    "Year\tQuarter\tMonth\tMachine Type\tDistinct count",
    "2025\tQ1\tJanuary\tExisting\t690",
    "2025\tQ1\tJanuary\tNew\t42",
    "2025\tQ1\tFebruary\tExisting\t704",
    "2025\tQ1\tFebruary\tNew\t38",
    "2025\tQ1\tMarch\tExisting\t711",
    "2025\tQ1\tMarch\tNew\t51",
    "2025\tQ2\tApril\tExisting\t730",
    "2025\tQ2\tApril\tNew\t66",
    "2025\tQ2\tMay\tExisting\t744",
    "2025\tQ2\tMay\tNew\t58",
    "2025\tQ2\tJune\tExisting\t751",
    "2025\tQ2\tJune\tNew\t62",
])

SAMPLE_LOCATIONS_TEXT = "\n".join([
    "ip_country\tip_region\tip_city\tMeasure Names\tproduct_name\tMeasure Values",
    "United States\tTexas\tAustin\tDistinct count of machine_id\tLabVIEW\t188",
    "United States\tTexas\tAustin\tDistinct count of machine_id\tTestStand\t142",
    "United States\tMichigan\tDetroit\tDistinct count of machine_id\tLabVIEW\t96",
    "United States\tMichigan\tDetroit\tDistinct count of machine_id\tTestStand\t71",
    "United States\tCalifornia\tSan Jose\tDistinct count of machine_id\tLabVIEW\t83",
])

SAMPLE_VERSIONS_TEXT = "\n".join([
    "product_name\tproduct_version\tDistinct count of machine_id",
    "LabVIEW\t2021\t399",
    "LabVIEW\t2024\t126",
    "TestStand\t2022\t188",
    "TestStand\t2024\t49",
    "VeriStand\t2023\t72",
])


def _load_example(key: str, text: str) -> None:
    st.session_state[key] = text


# --------------------------------------------------------------------------- #
# System self-check
# --------------------------------------------------------------------------- #
with st.expander("🔧 System check", expanded=False):
    import pptx as _pptx
    import PIL as _pil
    tess_path = shutil.which("tesseract")
    tess_status = f"found at {tess_path}" if tess_path else \
        "NOT FOUND — screenshot OCR disabled (fields can be typed manually)"
    preview_status = preview_renderer_status()
    preview_label = "available via macOS Quick Look" if preview_status["available"] else \
        "HTML preview available; PPTX image renderer not found"
    st.markdown(
        f"- Python **{platform.python_version()}** ({sys.executable})\n"
        f"- Streamlit **{st.__version__}** · pandas **{pd.__version__}** · "
        f"python-pptx **{_pptx.__version__}** · Pillow **{_pil.__version__}**\n"
        f"- Tesseract OCR: **{tess_status}**\n"
        f"- PPTX image preview: **{preview_label}**\n"
        f"- Platform: {platform.platform()}\n"
        f"- Profiles folder: `{prof.PROFILES_DIR}`"
    )

# --------------------------------------------------------------------------- #
# Profiles — save / load / batch
# --------------------------------------------------------------------------- #
def _apply_profile(name: str) -> None:
    """Button callback: load a profile into the widgets (runs pre-widget,
    so writing widget-backed session_state keys is allowed)."""
    payload = prof.load_profile(name)
    if not payload:
        st.session_state["profile_msg"] = ("error", f"Could not load '{name}'.")
        return
    for k, v in payload["texts"].items():
        st.session_state[k] = v
    for k, v in payload["fields"].items():
        st.session_state[k] = _truthy(v) if k == "f_systemlink_snow" else v
    st.session_state["finite_seed"] = pd.DataFrame(
        payload["finite_licenses"] or [],
        columns=["count", "license_type", "license_name"])
    st.session_state["bundle_seed"] = pd.DataFrame(
        {"bundle_name": pd.Series(payload["bundles"] or [], dtype="object")})
    _bump_editor_nonce()
    st.session_state["profile_msg"] = ("success", f"Loaded profile '{name}'.")


def _delete_profile(name: str) -> None:
    if prof.delete_profile(name):
        st.session_state["profile_msg"] = ("success", f"Deleted '{name}'.")
    else:
        st.session_state["profile_msg"] = ("error", f"'{name}' not found.")


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _support_scope_with_snow(scope: str, systemlink_snow: bool) -> str:
    parts = [str(scope or "").strip()]
    if systemlink_snow:
        parts.append("SystemLink Support (SNOW)")
    clean: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        key = part.lower()
        if key in seen:
            continue
        clean.append(part)
        seen.add(key)
    return " | ".join(clean)


def _data_from_profile(payload: dict) -> dict:
    """Assemble the slide-data dict from a saved profile (for batch mode)."""
    texts = payload.get("texts", {})
    fields = payload.get("fields", {})
    machine_df = dp.parse_machine_count(texts.get("machine_text", ""))
    locations_df = dp.parse_locations(texts.get("locations_text", ""))
    versions_df = dp.parse_usage_versions(texts.get("versions_text", ""))
    purchased_n = dp._to_number(fields.get("f_flex_purchased", ""))
    used_n = dp._to_number(fields.get("f_flex_used", ""))
    pct_used = (round(used_n / purchased_n * 100.0)
                if purchased_n and used_n is not None and purchased_n > 0
                else "—")
    support_scope = _support_scope_with_snow(
        fields.get("f_support_scope", ""),
        _truthy(fields.get("f_systemlink_snow", False)),
    )
    return {
        "service_id": fields.get("f_service_id", ""),
        "customer": fields.get("f_customer", ""),
        "updated_date": date.today().strftime("%d-%b-%Y"),
        "ea_end_date": fields.get("f_end_date", ""),
        "ep_term": fields.get("f_ep_term", ""),
        "contract_scope": fields.get("f_contract_scope", ""),
        "phase": fields.get("f_phase", ""),
        "debug_licenses": fields.get("f_debug", ""),
        "bundles": payload.get("bundles", []),
        "finite_licenses": payload.get("finite_licenses", []),
        "machine": {"df": machine_df,
                    "stats": dp.compute_machine_stats(machine_df)},
        "locations_top5": dp.top_locations(locations_df, 5),
        "versions_top5": dp.top_versions(versions_df, 5),
        "credits": {"purchased": fields.get("f_flex_purchased", "") or "—",
                    "used": fields.get("f_flex_used", "") or "—",
                    "pct_used": pct_used},
        "support": {"tier": fields.get("f_support_tier", "") or "—",
                    "scope": support_scope,
                    "systemlink_snow": _truthy(fields.get("f_systemlink_snow", False))},
    }


with st.expander("💾 Account profiles — save, load, batch", expanded=False):
    st.caption("Profiles store everything you've entered for an account as a "
               "local JSON file (nothing leaves this machine). Quarterly "
               "refresh: load the profile, paste the new tables, generate.")
    msg = st.session_state.pop("profile_msg", None)
    if msg:
        (st.success if msg[0] == "success" else st.error)(msg[1])

    saved = prof.list_profiles()
    pc1, pc2 = st.columns(2)
    with pc1:
        st.markdown("**Save current inputs**")
        default_name = prof.suggest_name(st.session_state)
        pname = st.text_input("Profile name", value=default_name,
                              key="profile_name")
        save_clicked = st.button("💾 Save profile", width="stretch")
    with pc2:
        st.markdown("**Load / delete a saved profile**")
        if saved:
            sel = st.selectbox("Saved profiles", saved, key="profile_select")
            lc, dc = st.columns(2)
            with lc:
                st.button("📂 Load", width="stretch",
                          on_click=_apply_profile, args=(sel,))
            with dc:
                st.button("🗑 Delete", width="stretch",
                          on_click=_delete_profile, args=(sel,))
        else:
            st.caption("No profiles saved yet.")

    st.markdown("**Batch: one deck, one slide per account**")
    batch_sel = st.multiselect("Profiles to include", saved,
                               key="batch_profiles")
    batch_insights = st.checkbox("Include a CSM Insights slide per account",
                                 value=True, key="batch_insights")
    if st.button("🛠️ Generate batch deck", disabled=not batch_sel,
                 width="stretch"):
        accounts = []
        skipped = []
        for name in batch_sel:
            payload = prof.load_profile(name)
            if not payload:
                skipped.append(name)
                continue
            d = _data_from_profile(payload)
            ins = generate_insights(d) if batch_insights else None
            accounts.append((d, ins))
        if skipped:
            st.warning("Skipped (couldn't load): " + ", ".join(skipped))
        if accounts:
            deck = build_deck(accounts)
            st.success(f"Deck built with {len(accounts)} account(s).")
            st.download_button(
                "⬇️ Download batch deck (.pptx)", data=deck,
                file_name="EA_batch_deck.pptx",
                mime=("application/vnd.openxmlformats-officedocument."
                      "presentationml.presentation"),
                width="stretch")

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
    st.button("Load example", key="load_machine_example",
              on_click=_load_example, args=("machine_text", SAMPLE_MACHINE_TEXT),
              width="stretch")
    machine_text = st.text_area("Machine count table", height=180,
                                key="machine_text", label_visibility="collapsed")

with c2:
    st.subheader("2. Locations")
    st.caption("Paste the geo export: **ip_country · ip_region · ip_city · "
               "Measure Names · product_name · Measure Values**  \n"
               "Aggregated to machines per city automatically. (A simple "
               "`Location · Count` table also works.)")
    avoid_location_double_count = st.checkbox(
        "Avoid product double-counting",
        value=True,
        help=("When the geo export is split by product, count each site once "
              "using the largest product row instead of summing product rows."),
    )
    st.button("Load example", key="load_locations_example",
              on_click=_load_example, args=("locations_text", SAMPLE_LOCATIONS_TEXT),
              width="stretch")
    locations_text = st.text_area("Locations table", height=180,
                                  key="locations_text",
                                  label_visibility="collapsed")

with c3:
    st.subheader("3. Usage Versions")
    st.caption("Paste: **product_name · product_version · Distinct count of "
               "machine_id**  \n"
               "e.g. `LabVIEW⇥2021⇥399`")
    st.button("Load example", key="load_versions_example",
              on_click=_load_example, args=("versions_text", SAMPLE_VERSIONS_TEXT),
              width="stretch")
    versions_text = st.text_area("Usage versions table", height=180,
                                 key="versions_text",
                                 label_visibility="collapsed")

# Live previews so the user can confirm parsing before generating.
machine_df = dp.parse_machine_count(machine_text)
locations_df = dp.parse_locations(
    locations_text,
    avoid_product_double_count=avoid_location_double_count,
)
versions_df = dp.parse_usage_versions(versions_text)

with st.expander("Preview parsed tables", expanded=False):
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        st.write("**Machine count**")
        st.dataframe(machine_df, width="stretch", hide_index=True)
    with pc2:
        st.write("**Locations**")
        st.dataframe(locations_df, width="stretch", hide_index=True)
    with pc3:
        st.write("**Usage versions**")
        st.dataframe(versions_df, width="stretch", hide_index=True)

# =========================================================================== #
# PART 2 — Upload screenshots (OCR -> editable review fields)
# =========================================================================== #
st.header("Part 2 · Upload screenshots")
st.warning("OCR is imperfect. **Every** value below is editable — review and "
           "correct everything before generating.")
st.caption("Screenshots B and C are **optional** — skip either one and its "
           "card is simply left out of the slide. You can also type rows in by "
           "hand below instead of uploading.")

up1, up2, up3 = st.columns(3)
with up1:
    img_a = st.file_uploader("Screenshot A — Contract details",
                             type=["png", "jpg", "jpeg", "bmp", "tiff"])
with up2:
    img_b = st.file_uploader("Screenshot B — Finite licenses (optional)",
                             type=["png", "jpg", "jpeg", "bmp", "tiff"])
with up3:
    img_c = st.file_uploader("Screenshot C — Unlimited bundles (optional)",
                             type=["png", "jpg", "jpeg", "bmp", "tiff"])


def _ocr_once(uploaded, state_key: str) -> str:
    """OCR an upload once (with word confidences) and cache the result,
    re-running only when the file changes."""
    fid = _file_id(uploaded)
    if fid is None:
        return st.session_state.get(state_key + "_text", "")
    if st.session_state.get(state_key + "_fid") != fid:
        try:
            detail = sr.ocr_image_detailed(uploaded)
        except RuntimeError as exc:
            st.error(str(exc))
            detail = {"text": "", "words": []}
        st.session_state[state_key + "_text"] = detail["text"]
        st.session_state[state_key + "_words"] = detail["words"]
        st.session_state[state_key + "_fid"] = fid
        st.session_state[state_key + "_new"] = True
    return st.session_state.get(state_key + "_text", "")


_FIELD_LABELS = {
    "service_id": "EA/EP Service ID", "customer": "Customer / Company",
    "start_date": "Start / Effective Date", "ep_term": "EP Term",
    "flex_credits": "FLEX credits purchased", "support_level": "Support tier",
    "debug_licenses": "Debug licenses",
}


def _confidence_report(parsed: dict, words: list[dict]) -> tuple[list, list]:
    """Split parsed contract fields into low-confidence and not-found lists."""
    low, missing = [], []
    for key, label in _FIELD_LABELS.items():
        value = parsed.get(key, "")
        if not value:
            missing.append(label)
            continue
        conf = sr.field_confidence(words, value)
        if conf is not None and conf < 70:
            low.append(f"{label} ({conf:.0f}%)")
    return low, missing


# --- Screenshot A: Contract details ---------------------------------------- #
st.subheader("Screenshot A · Contract details")
text_a = _ocr_once(img_a, "a")
if st.session_state.pop("a_new", False):
    parsed = sr.parse_contract_details(text_a)
    # Seed editable widget state only with values OCR actually found. This
    # keeps an imperfect OCR pass from wiping reviewed/profile-loaded fields.
    field_map = {
        "service_id": "f_service_id",
        "customer": "f_customer",
        "start_date": "f_start_date",
        "ep_term": "f_ep_term",
        "flex_credits": "f_flex_purchased",
        "support_level": "f_support_tier",
        "debug_licenses": "f_debug",
    }
    for parsed_key, state_key in field_map.items():
        value = parsed.get(parsed_key)
        if value:
            st.session_state[state_key] = value
    st.session_state.setdefault("f_debug", "No")
    if parsed.get("systemlink_snow"):
        st.session_state["f_systemlink_snow"] = True
    # Compute suggested End Date + Phase from Start Date + EP Term.
    start = dp.parse_date(st.session_state.get("f_start_date", ""))
    term = dp.parse_term_years(st.session_state.get("f_ep_term", ""))
    end = dp.compute_end_date(start, term)
    ph = dp.compute_phase(start, term)
    st.session_state["f_end_date"] = end.strftime("%d-%b-%Y").upper() if end else ""
    st.session_state["f_phase"] = ph["phase"]
    st.session_state["f_phase_hint"] = ph["hint"]
    low, missing = _confidence_report(
        parsed, st.session_state.get("a_words", []))
    st.session_state["a_report"] = (low, missing)

# Review-focus warnings from the last OCR run.
if st.session_state.get("a_report"):
    low, missing = st.session_state["a_report"]
    if low:
        st.warning("⚠️ Low OCR confidence — double-check: " + ", ".join(low))
    if missing:
        st.info("Not found in the screenshot — enter manually: "
                + ", ".join(missing))


def _recompute_end_phase():
    """Recompute EA End Date + Phase from the current Start Date + EP Term.

    Runs as a button callback (before widgets are rebuilt) so it can safely
    update the widget-backed session_state values.
    """
    start = dp.parse_date(st.session_state.get("f_start_date", ""))
    term = dp.parse_term_years(st.session_state.get("f_ep_term", ""))
    end = dp.compute_end_date(start, term)
    ph = dp.compute_phase(start, term)
    if end:
        st.session_state["f_end_date"] = end.strftime("%d-%b-%Y").upper()
    st.session_state["f_phase"] = ph["phase"]
    st.session_state["f_phase_hint"] = ph["hint"]


img_col_a, fields_col_a = st.columns([2, 3])
with img_col_a:
    if img_a is not None:
        st.image(img_a, caption="Screenshot A (for side-by-side review)",
                 width="stretch")
    else:
        st.caption("Upload Screenshot A to review it side-by-side here, or "
                   "type the fields directly.")

with fields_col_a:
    fa1, fa2 = st.columns(2)
    with fa1:
        st.text_input("EA/EP Service ID", key="f_service_id",
                      placeholder="EA-15725")
        st.text_input("Customer / Company", key="f_customer",
                      placeholder="RTX Corporation")
        st.text_input("Start / Effective Date", key="f_start_date",
                      placeholder="02-JAN-2026")
        st.text_input("EP Term", key="f_ep_term", placeholder="3 years")
        st.selectbox("Debug licenses included", ["Yes", "No"], key="f_debug")
    with fa2:
        st.text_input("EA End Date (computed — editable)", key="f_end_date",
                      placeholder="01-JAN-2029")
        st.button("↻ Recompute End Date & Phase",
                  help="Recompute from the current Start Date + EP Term",
                  on_click=_recompute_end_phase)
        st.text_input("Phase (computed — editable)", key="f_phase",
                      placeholder="Second Half")
        hint = st.session_state.get("f_phase_hint", "")
        if hint:
            st.caption(f"Hint: **{hint}**")
        st.text_input("Contract Scope (fill in — usually missing)",
                      key="f_contract_scope", placeholder="e.g. All NI software")

st.markdown("**Technical support**")
sc1, sc2, sc3 = st.columns([1, 1, 1])
with sc1:
    st.text_input("Support tier", key="f_support_tier",
                  placeholder="Enterprise Support")
with sc2:
    st.text_input("Support scope", key="f_support_scope",
                  placeholder="All Users")
with sc3:
    st.checkbox("SystemLink support (SNOW)", key="f_systemlink_snow",
                help="Adds SystemLink Support (SNOW) to the Technical Support card.")

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
st.subheader("Screenshot B · Finite licenses (optional)")
text_b = _ocr_once(img_b, "b")
if st.session_state.pop("b_new", False):
    rows = sr.parse_finite_licenses(text_b)
    st.session_state["finite_seed"] = pd.DataFrame(
        rows or [], columns=["count", "license_type", "license_name"]
    )
    _bump_editor_nonce()
if "finite_seed" not in st.session_state:
    st.session_state["finite_seed"] = pd.DataFrame(
        columns=["count", "license_type", "license_name"]
    )
img_col_b, ed_col_b = st.columns([2, 3])
with img_col_b:
    if img_b is not None:
        st.image(img_b, caption="Screenshot B", width="stretch")
    else:
        st.caption("Optional — upload Screenshot B, or type rows directly.")
with ed_col_b:
    st.caption("Columns: count · license type · license name. "
               "Edit/add/remove rows.")
    finite_edit = st.data_editor(
        st.session_state["finite_seed"], num_rows="dynamic",
        key=f"finite_editor_{_editor_nonce()}", width="stretch",
        column_config={
            "count": st.column_config.NumberColumn("Count", min_value=0,
                                                   step=1),
            "license_type": st.column_config.TextColumn("License Type"),
            "license_name": st.column_config.TextColumn("License Name"),
        },
    )
with st.expander("Raw OCR text — Screenshot B"):
    st.text(text_b or "(no text yet)")

# --- Screenshot C: Unlimited bundles --------------------------------------- #
st.subheader("Screenshot C · Unlimited bundles (optional)")
text_c = _ocr_once(img_c, "c")
if st.session_state.pop("c_new", False):
    bundles = sr.parse_unlimited_bundles(text_c)
    st.session_state["bundle_seed"] = pd.DataFrame(
        {"bundle_name": pd.Series(bundles or [], dtype="object")}
    )
    _bump_editor_nonce()
if "bundle_seed" not in st.session_state:
    st.session_state["bundle_seed"] = pd.DataFrame(
        {"bundle_name": pd.Series([], dtype="object")}
    )
img_col_c, ed_col_c = st.columns([2, 3])
with img_col_c:
    if img_c is not None:
        st.image(img_c, caption="Screenshot C", width="stretch")
    else:
        st.caption("Optional — upload Screenshot C, or type bundle names "
                   "directly.")
with ed_col_c:
    st.caption("One bundle name per row (the name after the colon). "
               "Edit/add/remove.")
    bundle_edit = st.data_editor(
        st.session_state["bundle_seed"], num_rows="dynamic",
        key=f"bundle_editor_{_editor_nonce()}", width="stretch",
        column_config={
            "bundle_name": st.column_config.TextColumn("Bundle Name")},
    )
with st.expander("Raw OCR text — Screenshot C"):
    st.text(text_c or "(no text yet)")

# =========================================================================== #
# PART 3 — Generate
# =========================================================================== #
st.header("Part 3 · Generate slide")


def _current_finite_rows() -> list[dict]:
    rows: list[dict] = []
    for _, r in finite_edit.iterrows():
        if not str(r.get("license_name") or r.get("license_type") or "").strip():
            continue
        count_n = dp._to_number(r.get("count"))
        rows.append({
            "count": int(count_n) if count_n is not None else 0,
            "license_type": str(r.get("license_type") or "").strip(),
            "license_name": str(r.get("license_name") or "").strip(),
        })
    return rows


def _current_bundles() -> list[str]:
    return [
        str(r["bundle_name"]).strip()
        for _, r in bundle_edit.iterrows()
        if str(r.get("bundle_name") or "").strip()
    ]


def _collect_data() -> dict:
    """Assemble the reviewed values + computed results into the slide payload."""
    stats = dp.compute_machine_stats(machine_df)
    purchased_n = dp._to_number(st.session_state.get("f_flex_purchased", ""))
    used_n = dp._to_number(st.session_state.get("f_flex_used", ""))
    systemlink_snow = bool(st.session_state.get("f_systemlink_snow", False))
    support_scope = _support_scope_with_snow(
        st.session_state.get("f_support_scope", ""),
        systemlink_snow,
    )
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
        "bundles": _current_bundles(),
        "finite_licenses": _current_finite_rows(),
        "machine": {"df": machine_df, "stats": stats},
        "locations_top5": dp.top_locations(locations_df, 5),
        "versions_top5": dp.top_versions(versions_df, 5),
        "credits": {
            "purchased": st.session_state.get("f_flex_purchased", "") or "—",
            "used": st.session_state.get("f_flex_used", "") or "—",
            "pct_used": pct_used if pct_used != "" else "—",
        },
        "support": {
            "tier": st.session_state.get("f_support_tier", "") or "—",
            "scope": support_scope,
            "systemlink_snow": systemlink_snow,
        },
    }


# Save-profile action (button rendered in the Profiles expander above; handled
# here so the editors' current rows are available).
if save_clicked:
    name = st.session_state.get("profile_name") or prof.suggest_name(
        st.session_state)
    path = prof.save_profile(name, st.session_state, _current_finite_rows(),
                             _current_bundles())
    st.toast(f"Profile saved: {path.name}")

include_insights_slide = st.checkbox(
    "Include a CSM Insights slide in the .pptx", value=True,
    key="include_insights")

generate = st.button("🛠️ Generate Slide", type="primary", width="stretch")

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
        items = generate_insights(data)
        try:
            pptx_buf = build_slide(
                data, insights=items if include_insights_slide else None)
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
            width="stretch",
        )

        # ----------------------------------------------------------------- #
        # On-page preview of the slide
        # ----------------------------------------------------------------- #
        st.subheader("Slide preview")
        st.caption("A faithful preview of the generated slide — adjust any "
                   "field above and click Generate again to refresh.")
        pptx_preview = render_pptx_preview(pptx_buf.getvalue())
        if pptx_preview.image_bytes:
            st.image(pptx_preview.image_bytes, caption=pptx_preview.message,
                     width="stretch")
        elif pptx_preview.message:
            st.caption(pptx_preview.message)
        components.html(generate_preview_html(data), height=700, scrolling=True)

        # ----------------------------------------------------------------- #
        # CSM insights (pure local computation)
        # ----------------------------------------------------------------- #
        st.subheader("🧠 CSM Insights")
        st.caption("Computed locally from your data — no LLM, no network.")
        if not items:
            st.info("Not enough data to generate insights yet.")
        for it in items:
            urgency = {1: "🔴", 2: "🟠", 3: "🟢", 4: "🔵"}.get(it["priority"], "•")
            st.markdown(f"{urgency} **{it['category']}** — {it['text']}")
