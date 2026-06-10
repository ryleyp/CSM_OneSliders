# EA Slide Builder

A small, **fully offline** web app for building Enterprise Agreement (EA)
one-slider PowerPoint slides. You run it on **your** PC; teammates open it in
their browser over your local network. Paste a few tables, upload three contract
screenshots, review the auto-parsed values, and click **Generate Slide** to get
a polished 16:9 `.pptx` plus on-page CSM insights.

> **Runs fully offline.** The app makes **no** network calls to outside services
> or external APIs. No telemetry, no "phone home." All data stays on your
> machine.

---

## What it does

- **Part 1 — Paste tables** (tab-separated, copied straight from Excel):
  1. **Machine Count** — New & Existing machines over time (period, new, existing)
  2. **Locations** — location and machine count
  3. **Usage Versions** — product, version, user count
- **Part 2 — Upload three screenshots**, read locally with OCR (Tesseract via
  `pytesseract`). Parsing is intentionally tolerant, and **every** parsed value
  lands in an **editable field you review and correct** before generating. OCR
  is imperfect — this review step is mandatory.
  - **Screenshot A — Contract details**: EA/EP Service ID, customer, start date,
    EP term, FLEX credits, support level, debug licenses. The app **computes a
    suggested EA End Date** (Start Date + EP Term) and the **Phase** (Not
    started / First Half / Second Half / Expired, with a "Year X of N" hint) —
    all editable.
  - **Screenshot B — Finite licenses**: count, license type, license name.
  - **Screenshot C — Unlimited bundles**: bundle names.
- **Part 3 — Generate Slide**: download the `.pptx` and read the CSM insights
  (computed locally — no LLM, no network).

---

## Easiest way to run (no command line)

On a **Mac**, you can start everything by double-clicking — no Terminal typing:

1. Make sure **Python 3** is installed (download from
   [python.org](https://www.python.org/downloads/) if not).
2. In Finder, open the project folder and **double-click
   `Start EA Slide Builder.command`**.
   - The **first** launch does a one-time setup (creates a local environment and
     installs dependencies) — it takes a minute or two.
   - After that, every launch is quick.
3. Your browser opens to the app automatically. The Terminal window that appears
   shows the address teammates can use (e.g. `http://192.168.1.42:8501`).
4. **Keep that window open** while using the app. Close it (or press `Ctrl+C`) to
   stop.

> First time only: if macOS says *"cannot be opened because it is from an
> unidentified developer,"* **right-click** the file → **Open** → **Open**. You
> only need to do this once.

For the screenshot OCR feature you still need system Tesseract installed once
(`brew install tesseract` — see below). Everything else the launcher handles.

The manual steps below do the same thing if you prefer the command line, or are
on Windows/Linux.

---

## Setup

### 1. Install Python dependencies

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

Pinned packages: `streamlit`, `pandas`, `python-pptx`, `openpyxl`,
`pytesseract`, `Pillow`.

### 2. Install system Tesseract OCR (separate, required for screenshots)

`pytesseract` is only a thin wrapper — the actual OCR engine, **Tesseract, must
be installed separately** as a system package:

- **Windows**: install the [UB Mannheim Tesseract build](https://github.com/UB-Mannheim/tesseract/wiki)
  and make sure `tesseract.exe` is on your `PATH` (or set
  `pytesseract.pytesseract.tesseract_cmd`).
- **macOS**: `brew install tesseract`
- **Debian/Ubuntu**: `sudo apt-get install tesseract-ocr`
- **Fedora**: `sudo dnf install tesseract`

If Tesseract is missing, the app still runs — it just shows a clear message and
you can type the screenshot values into the editable fields manually.

---

## Running it

From the project folder:

```bash
streamlit run app.py --server.address=0.0.0.0
```

- On your PC, open **http://localhost:8501**.
- Teammates on the **same local network** open **http://<your-PC-ip>:8501**.

### Find your PC's local IP

- **Windows**: run `ipconfig` and look for the **IPv4 Address** (e.g.
  `192.168.1.42`).
- **macOS**: run `ipconfig getifaddr en0` (Wi-Fi) or `en1`, or check **System
  Settings → Network**.
- **Linux**: run `hostname -I` and use the first address.

So if your IP is `192.168.1.42`, teammates go to `http://192.168.1.42:8501`.

### Important: availability & privacy

- The app is **only reachable while your PC is on and the app is running.** Close
  the terminal / shut down your PC and it goes away for everyone.
- It is meant for your **internal local network only**. **Do not** port-forward,
  tunnel, or otherwise expose it to the public internet.
- **All data stays in-house.** Nothing you paste or upload leaves your machine.

---

## Offline guarantee

This app runs **fully offline**. It does not contact any external service or
API, sends no telemetry, and never phones home. Streamlit's anonymous usage
stats are disabled in `.streamlit/config.toml` (`gatherUsageStats = false`).
All parsing, OCR, slide building, and insight generation happen locally.

---

## Project structure

| File | Responsibility |
| --- | --- |
| `app.py` | Streamlit UI (the one page; orchestrates everything) |
| `data_processor.py` | Parse the pasted tables + the three computations + contract date/phase math |
| `screenshot_reader.py` | Per-screenshot OCR parsers (A: contract, B: finite, C: bundles) |
| `slide_builder.py` | Build the 16:9 `.pptx` to the reference visual design |
| `insights.py` | Local CSM insight generation (no LLM) |
| `.streamlit/config.toml` | Local server + telemetry-off config |

---

## The slide

A single 16:9 slide with a dark-green (`#013324`) header band, three columns of
white rounded cards (thin gray borders), accent-green (`#18af7c`) section titles
and key numbers, a rendered line graph of total machine count, stat callouts,
styled tables, and a solid dark-green technical-support card.
