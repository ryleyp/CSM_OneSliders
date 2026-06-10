#!/bin/bash
#
# Double-click this file to download the latest version of EA Slide Builder.
# You only need to do this when you want updates — the app runs fine without it.
# After updating, start the app again with "Start EA Slide Builder.command".

cd "$(dirname "$0")" || exit 1

echo "Checking for updates to EA Slide Builder..."
echo

if ! command -v git >/dev/null 2>&1; then
  echo "Git is not installed, so automatic updates aren't available."
  echo "You can install Git from https://git-scm.com/download/mac, or download the"
  echo "latest files manually from GitHub. The app still works without updating."
  echo
  read -r -p "Press Enter to close..."
  exit 1
fi

# Pull the latest changes for whatever branch this copy is on.
if git pull; then
  echo
  echo "Up to date. Now start the app with 'Start EA Slide Builder.command'."
else
  echo
  echo "Update could not complete. If you changed files locally, that can block an"
  echo "update. Send the messages above for help. The app still works as-is."
fi

echo
read -r -p "Press Enter to close..."
