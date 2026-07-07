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
setlocal
set "PORT=8501"
set "PYTHON_CMD="
set "VENV_PY=.venv\Scripts\python.exe"

echo ============================================
echo    EA Slide Builder  (private / this PC only)
echo ============================================
echo.

REM --- Check Python is available --------------------------------------------
where python >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=python"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
  )
)

if not defined PYTHON_CMD (
  echo Python is not installed, or not on your PATH.
  echo Install it from https://www.python.org/downloads/ and during install
  echo check the box "Add Python to PATH", then double-click this file again.
  echo.
  echo If Python is already installed from the Microsoft Store, try installing
  echo the official python.org version instead.
  echo.
  pause
  exit /b 1
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Python 3.9 or newer is required.
  echo Install the latest Python 3 from https://www.python.org/downloads/
  echo and then double-click this file again.
  echo.
  pause
  exit /b 1
)

REM --- First-run setup: create the virtual environment ----------------------
if not exist ".venv\" (
  echo First-time setup: creating local environment ^(one time only^)...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo Could not create the environment.
    pause
    exit /b 1
  )
)

if not exist "%VENV_PY%" (
  echo The local environment is incomplete or damaged.
  echo Delete the .venv folder in this directory, then double-click this file again.
  echo.
  pause
  exit /b 1
)

REM --- Install dependencies if they're missing ------------------------------
"%VENV_PY%" -c "import streamlit" >nul 2>nul
if errorlevel 1 (
  echo Installing dependencies ^(one time only, this takes a minute or two^)...
  "%VENV_PY%" -m pip install --upgrade pip >nul 2>nul
  "%VENV_PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Dependency installation failed. Please send the messages above for help.
    pause
    exit /b 1
  )
)

REM --- Optional OCR system dependency ---------------------------------------
where tesseract >nul 2>nul
if errorlevel 1 (
  echo.
  echo Note: Tesseract OCR was not found.
  echo The app will still run, but screenshots will need manual entry until
  echo Tesseract is installed. The in-app System check shows this too.
)

REM --- Open the browser a few seconds after the server starts ----------------
start "" /min cmd /c "timeout /t 5 /nobreak >nul & start http://localhost:%PORT%"

echo.
echo Starting the app — PRIVATE, this PC only:
echo   http://localhost:%PORT%
echo.
echo Keep this window open while using the app. Close it to stop.
echo --------------------------------------------

REM Launch Streamlit bound to localhost only (127.0.0.1).
"%VENV_PY%" -m streamlit run app.py --server.address=127.0.0.1 --server.port=%PORT% --server.headless=true

echo.
echo The app has stopped.
pause
