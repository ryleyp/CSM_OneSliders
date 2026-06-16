@echo off
REM ==========================================================================
REM  Double-click this file to download the latest version of EA Slide Builder.
REM  You only need to do this when you want updates — the app runs fine without
REM  it. After updating, start the app again with "Start EA Slide Builder.bat".
REM ==========================================================================

cd /d "%~dp0"

echo Checking for updates to EA Slide Builder...
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo Git is not installed, so automatic updates aren't available.
  echo You can install Git from https://git-scm.com/download/win, or download the
  echo latest files manually from GitHub. The app still works without updating.
  echo.
  pause
  exit /b 1
)

git pull
if errorlevel 1 (
  echo.
  echo Update could not complete. If you changed files locally, that can block an
  echo update. Send the messages above for help. The app still works as-is.
) else (
  echo.
  echo Up to date. Now start the app with "Start EA Slide Builder.bat".
)

echo.
pause
