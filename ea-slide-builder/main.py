#!/usr/bin/env python3
"""
ea-slide-builder  —  offline EA account summary generator
Usage: python main.py --data <file> [options]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from contract_loader import load_contract
from data_processor import load_data
from insights import generate_insights
from slide_builder import build_slide


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="ea-slide-builder",
        description="Generate an EA account summary slide and CSM insights report. "
                    "Runs fully offline — no network calls.",
    )
    parser.add_argument(
        "--data", required=True,
        help="Path to usage data file (.csv or .xlsx with multiple tabs)",
    )
    parser.add_argument(
        "--pdf", default=None,
        help="Optional path to a contract PDF for auto-parsing contract fields",
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to a contract JSON config file (see contract_template.json)",
    )
    parser.add_argument(
        "--top-cities", type=int, default=5,
        help="Number of top city locations to display (default: 5)",
    )
    parser.add_argument(
        "--out", default="output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--no-prompt", action="store_true",
        help="Disable interactive prompts for missing contract fields",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load contract info
    # ------------------------------------------------------------------
    print("\n[1/3] Loading contract information...")
    contract = load_contract(
        config_path=args.config,
        pdf_path=args.pdf,
        interactive=not args.no_prompt,
    )

    ea_num   = contract.get("ea_number", "EA-XXXXXX").replace("/", "-")
    customer = contract.get("customer_name", "Customer").replace("/", "-")
    slug     = f"{ea_num}_{customer}".replace(" ", "_")

    # ------------------------------------------------------------------
    # 2. Load & process usage data
    # ------------------------------------------------------------------
    print(f"\n[2/3] Processing usage data from: {args.data}")
    data = load_data(args.data, top_cities=args.top_cities)

    tabs_found = list(data.keys())
    if not tabs_found:
        print("  [error] No recognisable data tabs found in the input file.")
        sys.exit(1)
    print(f"  Detected tabs: {', '.join(tabs_found)}")

    # ------------------------------------------------------------------
    # 3a. Build slide
    # ------------------------------------------------------------------
    pptx_path = out_dir / f"{slug}_summary.pptx"
    print(f"\n[3/3] Building outputs in: {out_dir}/")
    slide_out = build_slide(data, contract, pptx_path)
    print(f"  Slide  -> {slide_out}")

    # ------------------------------------------------------------------
    # 3b. Generate CSM insights
    # ------------------------------------------------------------------
    insights_md = generate_insights(data, contract)
    md_path = out_dir / f"{slug}_insights.md"
    md_path.write_text(insights_md, encoding="utf-8")
    print(f"  Insights -> {md_path}")

    print("\nDone. All files written locally. No network calls were made.\n")


if __name__ == "__main__":
    main()
