"""PyInstaller entry point for EA Slide Builder.

Boots the Streamlit runtime directly (no `streamlit run` subprocess, which
doesn't exist inside a frozen exe), bound to localhost only, then opens the
browser. Used by ea-slide-builder.spec — not needed for normal `streamlit run`
usage.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

PORT = 8501


def _base_dir() -> Path:
    """Folder containing the app files (PyInstaller unpacks to _MEIPASS)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def main() -> None:
    base = _base_dir()
    app_path = str(base / "app.py")

    # Private + quiet, matching .streamlit/config.toml.
    os.environ.setdefault("STREAMLIT_SERVER_ADDRESS", "127.0.0.1")
    os.environ.setdefault("STREAMLIT_SERVER_PORT", str(PORT))
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    threading.Timer(
        4.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()

    from streamlit.web import cli as stcli
    sys.argv = ["streamlit", "run", app_path,
                f"--server.port={PORT}", "--server.address=127.0.0.1",
                "--server.headless=true",
                "--browser.gatherUsageStats=false"]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
