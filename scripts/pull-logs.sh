#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="output/logs"
mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_FILE="$OUT_DIR/logcat-${STAMP}.txt"

adb get-state >/dev/null 2>&1 || {
  echo "No authorized Android device detected."
  exit 1
}

adb logcat -d > "$OUT_FILE"
echo "Saved logs to $OUT_FILE"
