#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 path/to/app.apk"
  exit 1
fi

APK_PATH="$1"

if [ ! -f "$APK_PATH" ]; then
  echo "APK not found: $APK_PATH"
  exit 1
fi

adb get-state >/dev/null 2>&1 || {
  echo "No authorized Android device detected."
  exit 1
}

adb install -r "$APK_PATH"
echo "Installed $APK_PATH"
