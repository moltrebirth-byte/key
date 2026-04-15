#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <package.name>"
  exit 1
fi

PKG_NAME="$1"

adb get-state >/dev/null 2>&1 || {
  echo "No authorized Android device detected."
  exit 1
}

echo "Clearing data for $PKG_NAME..."
adb shell pm clear "$PKG_NAME"
echo "Done."
