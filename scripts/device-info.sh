#!/usr/bin/env bash
set -euo pipefail

adb get-state >/dev/null 2>&1 || {
  echo "No authorized Android device detected."
  exit 1
}

echo "Serial: $(adb get-serialno)"
echo "Model: $(adb shell getprop ro.product.model | tr -d '\r')"
echo "Brand: $(adb shell getprop ro.product.brand | tr -d '\r')"
echo "Android: $(adb shell getprop ro.build.version.release | tr -d '\r')"
echo "SDK: $(adb shell getprop ro.build.version.sdk | tr -d '\r')"
