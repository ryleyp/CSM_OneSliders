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

**See [`WALKTHROUGH.md`](WALKTHROUGH.md) for the full step-by-step install &
run guide for Mac and Windows** — written for non-technical users.

The short version: just **double-click the launcher** for your system.

- **Mac:** `Start EA Slide Builder.command`
- **Windows:** `Start EA Slide Builder.bat`

The first launch sets up a local environment and installs dependencies (one
time, a minute or two); after that it opens your browser to the app
automatically. Keep the window that opens — close it to stop the app. To get
updates later, double-click **`Update EA Slide Builder`** (`.command` on Mac,
`.bat` on Windows). You do **not** need to update to use the app.

> **Private by default.** The launchers run the app on **localhost only**
> (`http://localhost:8501`) — reachable from **this machine only**, not your
> network or the internet. Any contract data you enter stays on your computer.

The manual command-line steps below do the same thing, if you prefer.

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

From the project folder (private — this machine only):

```bash
streamlit run app.py
```

- Open **http://localhost:8501** on this computer.
- The app is bound to localhost only, so nothing on your network or the
  internet can reach it. This is the recommended mode for contract data.

> **Optional, not recommended for contract data:** to deliberately let teammates
> on your local network open it, launch with `--server.address=0.0.0.0` and they
> visit `http://<your-PC-ip>:8501`. Only do this on a trusted network, and never
> expose it to the public internet.

### Find your PC's local IP (only if you opted into network sharing)

- **Windows**: run `ipconfig` and look for the **IPv4 Address** (e.g.
  `192.168.1.42`).
- **macOS**: run `ipconfig getifaddr en0` (Wi-Fi) or `en1`, or check **System
  Settings → Network**.
- **Linux**: run `hostname -I` and use the first address.

So if your IP is `192.168.1.42`, teammates go to `http://192.168.1.42:8501`.

### Important: privacy & contract data

- **Default is private** — the app is reachable **only on this machine**. Your
  data, including any contract info you enter, stays here.
- **Keep contract data in-house.** Don't post the screenshots or generated
  slide to public locations; share the finished slide only via approved internal
  channels.
- **Never expose it to the public internet** — no port-forwarding or tunneling.
- The app is **only reachable while your PC is on and the app is running.**

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
