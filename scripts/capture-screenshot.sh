#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="output/screenshots"
mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
REMOTE_PATH="/sdcard/Download/screen-${STAMP}.png"
LOCAL_PATH="$OUT_DIR/screen-${STAMP}.png"

adb get-state >/dev/null 2>&1 || {
  echo "No authorized Android device detected."
  exit 1
}

adb shell screencap -p "$REMOTE_PATH"
adb pull "$REMOTE_PATH" "$LOCAL_PATH" >/dev/null
adb shell rm "$REMOTE_PATH"

echo "Saved screenshot to $LOCAL_PATH"
