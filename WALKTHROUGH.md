# EA Slide Builder — Install & Run Guide (Mac & Windows)

A plain-English walkthrough to set up EA Slide Builder as a **double-click app**
on your own computer. No command-line knowledge required.

---

## 🔒 Privacy first — read this

This tool is built to keep your data on your own machine.

- **Everything stays local.** Tables you paste, screenshots you upload, and the
  slide you generate are processed **only on this computer**. The app makes no
  internet calls, sends no telemetry, and uses no external services.
- **It runs in PRIVATE mode.** The double-click launchers start the app bound to
  **localhost only** (`http://localhost:8501`). That means **only this computer
  can open it** — nobody on your office network or the internet can reach it.
- **Contract information must not be shared out.** If you enter contract details
  (customer names, EA numbers, dates, credits, license counts, etc.), that
  information **lives on this machine and should stay here.** Do not post the
  generated files or screenshots to public locations. Share the finished slide
  only through your normal, approved internal channels.
- **Do not expose it to the internet.** Don't port-forward it, tunnel it, or
  change it to be network-reachable unless you fully understand the risk. The
  private launchers already prevent this by default.

> Bottom line: treat anything you put into this app like the confidential
> contract data it is. It stays on your computer.

---

## What you need (one time)

| | Mac | Windows |
| --- | --- | --- |
| **Python 3** (required) | [Download](https://www.python.org/downloads/) and install | [Download](https://www.python.org/downloads/) — during install, **check "Add Python to PATH"** |
| **Git** (optional, for updates) | [Download](https://git-scm.com/download/mac) | [Download](https://git-scm.com/download/win) |
| **Tesseract OCR** (optional, for the screenshot feature) | `brew install tesseract` | [UB Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) |

You can run the app **without Git** and **without Tesseract** — see the notes
below. Python is the only hard requirement.

---

## Step 1 — Get the files onto your computer

You only do this once. Two ways:

### Option A — Download a ZIP (no Git needed)
1. Go to the project page on GitHub.
2. Click the green **Code** button → **Download ZIP**.
3. Unzip it somewhere you'll remember (e.g. Documents).

> With the ZIP method you can still **run** the app fine. To get **updates**
> later you'd download a fresh ZIP, or install Git and use the Update launcher.

### Option B — Clone with Git (recommended if you want easy updates)
- **Mac:** open Terminal and run:
  ```
  cd ~/Documents
  git clone <repository-url>
  ```
- **Windows:** open Command Prompt and run:
  ```
  cd %USERPROFILE%\Documents
  git clone <repository-url>
  ```

(Replace `<repository-url>` with the repo's URL. After cloning you have a
`CSM_OneSliders` folder.)

---

## Step 2 — Start the app (double-click)

Open the project folder and double-click the launcher for your system:

- **Mac:** `Start EA Slide Builder.command`
- **Windows:** `Start EA Slide Builder.bat`

What happens:
1. **First time only:** it sets up a local environment and installs the
   dependencies. This takes a minute or two — let it finish.
2. It starts the app and **opens your browser** to `http://localhost:8501`.
3. A small Terminal/Command window stays open. **Keep it open** while you use
   the app.

### First-time security prompts
- **Mac:** if you see *"cannot be opened because it is from an unidentified
  developer,"* **right-click** the launcher → **Open** → **Open**. One time only.
- **Windows:** if SmartScreen shows *"Windows protected your PC,"* click **More
  info** → **Run anyway**. One time only.

### To stop the app
Close the Terminal/Command window, or press **Ctrl+C** inside it. The app is
gone until you start it again.

---

## Running WITHOUT updating

**You do not need to update to use the app.** Once it's installed, just
double-click the **Start** launcher whenever you want to use it. It runs the
copy you already have — no internet required to run, no Git required, no pulling
changes. Day to day, the only thing you ever do is double-click **Start**.

Updating is **optional** and only matters when you specifically want the latest
improvements.

---

## Getting updates (optional)

When you want the newest version, double-click the **Update** launcher:

- **Mac:** `Update EA Slide Builder.command`
- **Windows:** `Update EA Slide Builder.bat`

It downloads the latest files, then tells you to start the app again. (This
needs **Git** installed — see the table above. If you used the ZIP method
without Git, just download a fresh ZIP instead.)

Prefer the command line? You can update manually:
- **Mac:** `cd` into the folder, then `git pull`
- **Windows:** `cd` into the folder, then `git pull`

After any update, start the app normally with the **Start** launcher. You only
need to re-run setup if we tell you the dependencies changed (the launcher
handles that automatically anyway).

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| **"Python is not installed"** | Install Python 3 (links above). On Windows, re-run the installer and check **"Add Python to PATH."** |
| **Browser didn't open** | Manually go to **http://localhost:8501**. |
| **"Port 8501 is already in use"** | The app may already be running in another window — use that one, or close it and relaunch. |
| **Screenshot OCR does nothing** | Install **Tesseract** (links above). The app still works without it — just type the screenshot values into the editable fields. |
| **Update says it "could not complete"** | You may have edited files locally. Send us the message shown; the app still works as-is. |
| **Mac: "unidentified developer"** | Right-click the launcher → **Open** → **Open**. |
| **Windows: SmartScreen warning** | **More info** → **Run anyway**. |

---

## Quick reference

- **Use the app:** double-click **Start EA Slide Builder** → browser opens →
  keep the window open → close it to stop.
- **Update the app (optional):** double-click **Update EA Slide Builder**.
- **Where your data lives:** only on this computer. Keep contract info here.
  Saved **account profiles** live in the `profiles/` folder next to the app —
  they contain contract data, so treat that folder as confidential (it is
  excluded from Git automatically).
- **Health check:** open the **🔧 System check** expander at the top of the app
  to see versions and whether Tesseract is installed; or run
  `python -m tests.run_all` from the project folder for a full self-test.
- **No-Python distribution (advanced):** see `packaging/BUILD_EXE.md` to build
  a double-click `.exe` folder for teammates.
