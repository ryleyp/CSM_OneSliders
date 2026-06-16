#!/bin/bash
#
# Double-click this file in Finder to start EA Slide Builder — no command line
# needed. The first run does a one-time setup (creates a local Python
# environment and installs dependencies); after that it just launches.
#
# PRIVATE MODE: the app is reachable ONLY on this Mac (http://localhost:8501).
# Nobody else on your network or the internet can open it. Your data — including
# any contract info you enter — stays on this machine.
#
# Keep the Terminal window that opens — the app runs only while it's open.
# Close the window (or press Ctrl+C) to stop the app.

# Move to this script's own folder so double-clicking works from anywhere.
cd "$(dirname "$0")" || exit 1

PORT=8501

echo "============================================"
echo "   EA Slide Builder  (private / this Mac only)"
echo "============================================"

# --- Check Python 3 is available ------------------------------------------- #
if ! command -v python3 >/dev/null 2>&1; then
  echo
  echo "Python 3 is not installed. Install it from https://www.python.org/downloads/"
  echo "then double-click this file again."
  echo
  read -r -p "Press Enter to close..."
  exit 1
fi

# --- First-run setup: create the virtual environment ----------------------- #
if [ ! -d ".venv" ]; then
  echo
  echo "First-time setup: creating local environment (one time only)..."
  python3 -m venv .venv || {
    echo "Could not create the environment."
    read -r -p "Press Enter to close..."
    exit 1
  }
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# --- Install dependencies if they're missing ------------------------------- #
if ! python3 -c "import streamlit" >/dev/null 2>&1; then
  echo
  echo "Installing dependencies (one time only, this takes a minute or two)..."
  python3 -m pip install --upgrade pip >/dev/null 2>&1
  python3 -m pip install -r requirements.txt || {
    echo "Dependency installation failed. Please send the messages above for help."
    read -r -p "Press Enter to close..."
    exit 1
  }
fi

# --- Start the app (private: localhost only) and open the browser ---------- #
echo
echo "Starting the app — PRIVATE, this Mac only:"
echo "  http://localhost:$PORT"
echo
echo "Keep this window open while using the app. Close it to stop."
echo "--------------------------------------------"

# Open the browser shortly after the server starts.
( sleep 4; open "http://localhost:$PORT" >/dev/null 2>&1 ) &

# Launch Streamlit bound to localhost only (127.0.0.1) so nothing on the
# network can reach it. headless = don't let Streamlit open its own tab.
python3 -m streamlit run app.py \
  --server.address=127.0.0.1 \
  --server.port="$PORT" \
  --server.headless=true

# If Streamlit exits, pause so the user can read any message.
echo
read -r -p "The app has stopped. Press Enter to close..."
