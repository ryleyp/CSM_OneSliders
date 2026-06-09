"""
Local Flask server for ea-slide-builder.
Runs on http://localhost:5000 — no external network calls.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

# Allow imports from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from contract_loader import load_contract
from data_processor import load_data
from insights import generate_insights
from slide_builder import build_slide

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload limit

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    errors = []

    # --- Data file ---
    data_file = request.files.get("data_file")
    if not data_file or data_file.filename == "":
        return jsonify({"error": "Please upload a usage data file (.csv or .xlsx)."}), 400

    suffix = Path(data_file.filename).suffix.lower()
    if suffix not in (".csv", ".xlsx", ".xls"):
        return jsonify({"error": "Data file must be .csv or .xlsx"}), 400

    # --- Contract fields from form ---
    contract: dict = {
        "ea_number":              request.form.get("ea_number", "").strip(),
        "customer_name":          request.form.get("customer_name", "").strip(),
        "ea_end_date":            request.form.get("ea_end_date", "").strip(),
        "term_duration":          request.form.get("term_duration", "").strip(),
        "contract_scope":         request.form.get("contract_scope", "").strip(),
        "phase":                  request.form.get("phase", "").strip(),
        "technical_support_level": request.form.get("technical_support_level", "Standard").strip(),
    }

    try:
        contract["training_credits_total"] = int(request.form.get("training_credits_total") or 0)
        contract["training_credits_used"]  = int(request.form.get("training_credits_used") or 0)
    except ValueError:
        contract["training_credits_total"] = 0
        contract["training_credits_used"]  = 0

    # Parse JSON fields for bundles and licenses
    try:
        contract["bundles"] = json.loads(request.form.get("bundles") or "[]")
    except json.JSONDecodeError:
        contract["bundles"] = []

    try:
        contract["finite_quantity_licenses"] = json.loads(
            request.form.get("finite_quantity_licenses") or "[]"
        )
    except json.JSONDecodeError:
        contract["finite_quantity_licenses"] = []

    # --- Optional PDF upload ---
    pdf_file = request.files.get("pdf_file")

    top_cities = int(request.form.get("top_cities") or 5)

    # Write uploads to temp files
    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = Path(tmpdir) / data_file.filename
        data_file.save(data_path)

        # If PDF was uploaded, let contract_loader parse it then merge
        if pdf_file and pdf_file.filename:
            pdf_path = Path(tmpdir) / pdf_file.filename
            pdf_file.save(pdf_path)
            pdf_contract = load_contract(
                config_path=None, pdf_path=pdf_path, interactive=False
            )
            # PDF fills in any blanks left by the form
            for k, v in pdf_contract.items():
                if not contract.get(k):
                    contract[k] = v

        # Process data
        try:
            data = load_data(data_path, top_cities=top_cities)
        except Exception as e:
            return jsonify({"error": f"Could not read data file: {e}"}), 400

        if not data:
            return jsonify({"error": "No recognisable data tabs found in the file."}), 400

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

    tabs_found = list(data.keys())
    return jsonify({
        "ok": True,
        "tabs_found": tabs_found,
        "pptx_name": pptx_path.name,
        "md_name":   md_path.name,
        "insights":  insights_md,
    })


@app.route("/download/<filename>")
def download(filename: str):
    # Sanitise: only allow files inside OUTPUT_DIR
    safe = OUTPUT_DIR / Path(filename).name
    if not safe.exists():
        return "File not found", 404
    return send_file(safe, as_attachment=True)


def open_browser():
    webbrowser.open("http://localhost:5000")


def run():
    # Open browser after a short delay so the server is ready
    threading.Timer(1.2, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    run()
