@echo off
REM ==========================================================================
REM  Double-click this file to start EA Slide Builder on Windows — no command
REM  line needed. The first run does a one-time setup (creates a local Python
REM  environment and installs dependencies); after that it just launches.
REM
REM  PRIVATE MODE: the app is reachable ONLY on this PC (http://localhost:8501).
REM  Nobody else on your network or the internet can open it. Your data —
REM  including any contract info you enter — stays on this machine.
REM
REM  Keep the window that opens — the app runs only while it's open.
REM  Close the window (or press Ctrl+C) to stop the app.
REM ==========================================================================

cd /d "%~dp0"
set PORT=8501

echo ============================================
echo    EA Slide Builder  (private / this PC only)
echo ============================================
echo.

REM --- Check Python is available --------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed, or not on your PATH.
  echo Install it from https://www.python.org/downloads/ and during install
  echo check the box "Add Python to PATH", then double-click this file again.
  echo.
  pause
  exit /b 1
)

REM --- First-run setup: create the virtual environment ----------------------
if not exist ".venv\" (
  echo First-time setup: creating local environment ^(one time only^)...
  python -m venv .venv
  if errorlevel 1 (
    echo Could not create the environment.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

REM --- Install dependencies if they're missing ------------------------------
python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
  echo Installing dependencies ^(one time only, this takes a minute or two^)...
  python -m pip install --upgrade pip >nul 2>nul
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Dependency installation failed. Please send the messages above for help.
    pause
    exit /b 1
  )
)

REM --- Open the browser a few seconds after the server starts ----------------
start "" /min cmd /c "timeout /t 5 /nobreak >nul & start "" http://localhost:%PORT%"

echo.
echo Starting the app — PRIVATE, this PC only:
echo   http://localhost:%PORT%
echo.
echo Keep this window open while using the app. Close it to stop.
echo --------------------------------------------

REM Launch Streamlit bound to localhost only (127.0.0.1).
python -m streamlit run app.py --server.address=127.0.0.1 --server.port=%PORT% --server.headless=true

echo.
echo The app has stopped.
pause
