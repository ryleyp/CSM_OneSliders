"""
Local Flask server for ea-slide-builder.
Runs on http://localhost:5000 — no external network calls.
"""
from __future__ import annotations

import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract_loader import load_contract
from data_processor import load_data
from insights import generate_insights
from slide_builder import build_slide

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    # --- Data file (required) ---
    data_file = request.files.get("data_file")
    if not data_file or not data_file.filename:
        return jsonify({"error": "Please upload a usage data file (.csv or .xlsx)."}), 400
    if Path(data_file.filename).suffix.lower() not in (".csv", ".xlsx", ".xls"):
        return jsonify({"error": "Data file must be .csv or .xlsx"}), 400

    # --- PDF (optional) ---
    pdf_file = request.files.get("pdf_file")

    # --- Training credits remaining (optional number) ---
    tc_remaining_raw = request.form.get("tc_remaining", "").strip()
    tc_remaining = int(tc_remaining_raw) if tc_remaining_raw.isdigit() else None

    # --- Top-N cities ---
    try:
        top_cities = int(request.form.get("top_cities") or 5)
    except ValueError:
        top_cities = 5

    # --- Top-N versions per product ---
    top_versions_raw = request.form.get("top_versions", "").strip()
    top_versions = int(top_versions_raw) if top_versions_raw.isdigit() else None

    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = Path(tmpdir) / data_file.filename
        data_file.save(data_path)

        pdf_path = None
        if pdf_file and pdf_file.filename:
            pdf_path = Path(tmpdir) / pdf_file.filename
            pdf_file.save(pdf_path)

        # Load contract from PDF only (no manual form fields)
        contract = load_contract(
            config_path=None,
            pdf_path=pdf_path,
            tc_remaining=tc_remaining,
            interactive=False,
        )

        # Process usage data
        try:
            data = load_data(data_path, top_cities=top_cities, top_versions=top_versions)
        except Exception as e:
            return jsonify({"error": f"Could not read data file: {e}"}), 400

        if not data:
            return jsonify({"error": "No recognisable data tabs found. Check that your file has columns for Year/Quarter, Product/Version, or City/Country."}), 400

        # Build outputs
        ea_num   = (contract.get("ea_number") or "EA").replace("/", "-")
        customer = (contract.get("customer_name") or "Customer").replace("/", "-")
        slug     = f"{ea_num}_{customer}".replace(" ", "_")

        pptx_path = OUTPUT_DIR / f"{slug}_summary.pptx"
        md_path   = OUTPUT_DIR / f"{slug}_insights.md"

        try:
            build_slide(data, contract, pptx_path)
        except Exception as e:
            return jsonify({"error": f"Slide build failed: {e}"}), 500

        try:
            insights_md = generate_insights(data, contract)
            md_path.write_text(insights_md, encoding="utf-8")
        except Exception as e:
            return jsonify({"error": f"Insights generation failed: {e}"}), 500

    return jsonify({
        "ok":        True,
        "tabs_found": list(data.keys()),
        "pptx_name": pptx_path.name,
        "md_name":   md_path.name,
        "insights":  insights_md,
        "contract_preview": {
            "ea_number":     contract.get("ea_number", ""),
            "customer_name": contract.get("customer_name", ""),
            "ea_end_date":   contract.get("ea_end_date", ""),
            "term_duration": contract.get("term_duration", ""),
            "n_licenses":    len(contract.get("finite_quantity_licenses", [])),
            "n_bundles":     len(contract.get("bundles", [])),
        },
    })


@app.route("/download/<filename>")
def download(filename: str):
    safe = OUTPUT_DIR / Path(filename).name
    if not safe.exists():
        return "File not found", 404
    return send_file(safe, as_attachment=True)


def open_browser():
    webbrowser.open("http://localhost:5000")


def run():
    threading.Timer(1.2, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    run()
