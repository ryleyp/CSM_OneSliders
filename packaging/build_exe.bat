@echo off
REM ==========================================================================
REM  Build "EA Slide Builder.exe" on Windows with PyInstaller.
REM  Run this ON the Windows machine (exes must be built on their target OS).
REM  Double-click, or run from the project root. See BUILD_EXE.md for details.
REM ==========================================================================

cd /d "%~dp0.."
setlocal
set "PYTHON_CMD="
set "VENV_PY=.venv\Scripts\python.exe"

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
  echo Install Python 3.9+ from https://www.python.org/downloads/
  echo and check "Add Python to PATH" during install.
  pause
  exit /b 1
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Python 3.9 or newer is required.
  pause
  exit /b 1
)

if not exist ".venv\" (
  echo Creating build environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo Could not create the build environment.
    pause
    exit /b 1
  )
)

if not exist "%VENV_PY%" (
  echo The local environment is incomplete or damaged.
  echo Delete the .venv folder, then run this file again.
  pause
  exit /b 1
)

echo Installing app dependencies + PyInstaller...
"%VENV_PY%" -m pip install --upgrade pip >nul 2>nul
"%VENV_PY%" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

echo Building the exe (this takes a few minutes)...
"%VENV_PY%" -m PyInstaller packaging\ea-slide-builder.spec --noconfirm
if errorlevel 1 (
  echo Build failed. Send the messages above for help.
  pause
  exit /b 1
)

echo.
echo Done. The app folder is:  dist\EA Slide Builder\
echo Distribute that whole folder; teammates double-click "EA Slide Builder.exe".
echo (Screenshot OCR still requires Tesseract installed on each machine.)
pause
