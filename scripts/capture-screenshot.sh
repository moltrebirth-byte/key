#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="output/screenshots"
mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"

adb get-state >/dev/null 2>&1 || {
  echo "No authorized Android device detected."
  exit 1
}

if [[ "${1:-}" == "--record" ]]; then
  DURATION="${2:-10}"
  REMOTE_PATH="/sdcard/Download/screen-${STAMP}.mp4"
  LOCAL_PATH="$OUT_DIR/screen-${STAMP}.mp4"
  echo "Recording screen for $DURATION seconds..."
  adb shell screenrecord --time-limit "$DURATION" "$REMOTE_PATH"
  echo "Pulling video..."
  adb pull "$REMOTE_PATH" "$LOCAL_PATH" >/dev/null
  adb shell rm "$REMOTE_PATH"
  echo "Saved screen recording to $LOCAL_PATH"
else
  REMOTE_PATH="/sdcard/Download/screen-${STAMP}.png"
  LOCAL_PATH="$OUT_DIR/screen-${STAMP}.png"
  adb shell screencap -p "$REMOTE_PATH"
  adb pull "$REMOTE_PATH" "$LOCAL_PATH" >/dev/null
  adb shell rm "$REMOTE_PATH"
  echo "Saved screenshot to $LOCAL_PATH"
fi
