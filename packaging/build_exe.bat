@echo off
REM ==========================================================================
REM  Build "EA Slide Builder.exe" on Windows with PyInstaller.
REM  Run this ON the Windows machine (exes must be built on their target OS).
REM  Double-click, or run from the project root. See BUILD_EXE.md for details.
REM ==========================================================================

cd /d "%~dp0.."

if not exist ".venv\" (
  echo Creating build environment...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo Installing app dependencies + PyInstaller...
python -m pip install --upgrade pip >nul 2>nul
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

echo Building the exe (this takes a few minutes)...
python -m PyInstaller packaging\ea-slide-builder.spec --noconfirm
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
