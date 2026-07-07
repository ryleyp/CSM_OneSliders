@echo off
REM ==========================================================================
REM  Double-click this file to download the latest version of EA Slide Builder.
REM  You only need to do this when you want updates — the app runs fine without
REM  it. After updating, start the app again with "Start EA Slide Builder.bat".
REM ==========================================================================

cd /d "%~dp0"

echo Checking for updates to EA Slide Builder...
echo.

if not exist ".git\" (
  echo This folder is a ZIP download, not a Git copy, so it cannot self-update.
  echo ^(The tell-tale sign: the folder name contains "CSM_OneSliders-claude-...".^)
  echo.
  echo To get updates, make a one-time Git copy instead:
  echo   1. Open PowerShell
  echo   2. cd %%USERPROFILE%%
  echo   3. git clone https://github.com/ryleyp/CSM_OneSliders.git EA
  echo   4. Use the EA folder from now on ^(and delete this one^).
  echo.
  echo The app itself still works from this folder - it just won't update.
  pause
  exit /b 1
)

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
