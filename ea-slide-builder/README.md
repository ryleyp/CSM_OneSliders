# ea-slide-builder

Generate a one-slide PowerPoint account summary and a CSM insights markdown
report from an EA usage spreadsheet.

**Runs fully offline — no network calls, no telemetry, no external APIs.**

---

## Requirements

- Python 3.9+
- Dependencies pinned in `requirements.txt`

```
pip install -r requirements.txt
```

---

## Running the App (recommended)

```bash
python app/server.py
```

Opens automatically at **http://localhost:5000** in your browser. Upload your
data file, fill in the contract fields, and click **Generate**. Download the
`.pptx` and insights report directly from the page.

---

## CLI Usage (alternative)

```bash
python main.py --data <data_file> [options]
```

### Required

| Flag | Description |
|------|-------------|
| `--data` | Path to usage data (`.csv` or multi-tab `.xlsx`) |

### Optional

| Flag | Default | Description |
|------|---------|-------------|
| `--config` | — | Path to a JSON contract config file (see `contract_template.json`) |
| `--pdf` | — | Path to a contract PDF for local field extraction (pdfplumber + regex) |
| `--top-cities` | `5` | Number of top locations to display |
| `--out` | `output` | Output directory |
| `--no-prompt` | off | Disable interactive prompts for missing contract fields |

### Examples

```bash
# Minimal — uses interactive prompts for missing contract fields
python main.py --data usage.xlsx

# Full — JSON config + PDF + custom top-cities count
python main.py \
  --data usage.xlsx \
  --config my_contract.json \
  --pdf contract.pdf \
  --top-cities 10 \
  --out ./reports

# Fully non-interactive (CI/batch)
python main.py --data usage.xlsx --config my_contract.json --no-prompt
```

---

## Contract Config

Copy and edit `contract_template.json`:

```json
{
  "ea_number": "EA-123456",
  "customer_name": "Acme Corporation",
  "ea_end_date": "2025-12-31",
  "term_duration": "3 Years",
  "contract_scope": "Enterprise",
  "phase": "Phase 2",
  "training_credits_total": 40,
  "training_credits_used": 12,
  "technical_support_level": "Premier",
  "bundles": [
    {"name": "Design Suite Bundle", "type": "Suite"}
  ],
  "finite_quantity_licenses": [
    {"count": 500, "name": "AutoCAD", "type": "Named User"}
  ]
}
```

Contract fields are resolved in priority order:
1. `--config` JSON file
2. `--pdf` parsed locally with pdfplumber + regex
3. Interactive prompts for anything still blank

---

## Input Data Format

The tool detects tabs by column content, not tab name.

### Machines tab (usage trend)
Required columns: `Year`, `Quarter` or `Month`, `Machine Type` (values "New"/"Existing"), and a count column (e.g. `Session Count`).

### Software tab
Required columns: a product name column and a usage count column. Optional: `Version`.

### Cities tab
Required columns: `City` and/or `Country`, plus a usage count column.

For `.xlsx` files, put each tab type on a separate sheet.
For `.csv`, a single sheet can contain any one of the three tab types.

---

## Outputs

Both files are written to `--out` (default: `./output`):

| File | Description |
|------|-------------|
| `<EA>_<Customer>_summary.pptx` | 16:9 one-slide account summary with trend chart |
| `<EA>_<Customer>_insights.md` | Prioritized CSM findings grounded in the data |

### Slide layout

```
┌─────────────────────────────────────────────────────────────────┐
│ EA-XXXXXX - Customer Name                                        │
├─────────────────────────────────────────────────────────────────┤
│  EA End Date | Term | Scope | Phase                              │
├──────────────────┬────────────────────┬─────────────────────────┤
│ Bundle Info      │ Software Trend     │ Top Locations           │
│ License Table    │ Chart + Data Table │ Version Usage           │
│                  │                    │ Training Credits        │
│                  │                    │ Technical Support       │
└──────────────────┴────────────────────┴─────────────────────────┘
```

Theme: dark green `#013324` headers, accent green `#18af7c` trend line and rounded box border.

---

## Generating Sample Data

```bash
python generate_sample.py
# Creates sample_data/sample_usage.xlsx and sample_data/sample_machines.csv
```

Then run:

```bash
python main.py --data sample_data/sample_usage.xlsx --config contract_template.json --no-prompt
```

---

## Offline Guarantee

This tool makes **zero network calls**. All processing is local:
- `pandas` for data computation
- `python-pptx` for slide generation
- `pdfplumber` for local PDF parsing
- `openpyxl` for `.xlsx` reading

No `requests`, no `httpx`, no telemetry, no external APIs of any kind.
