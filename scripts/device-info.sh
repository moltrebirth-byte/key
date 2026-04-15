#!/usr/bin/env bash
set -euo pipefail

adb get-state >/dev/null 2>&1 || {
  echo "No authorized Android device detected."
  exit 1
}

echo "=== Basic Info ==="
echo "Serial: $(adb get-serialno)"
echo "Model: $(adb shell getprop ro.product.model | tr -d '\r')"
echo "Brand: $(adb shell getprop ro.product.brand | tr -d '\r')"
echo "Android: $(adb shell getprop ro.build.version.release | tr -d '\r')"
echo "SDK: $(adb shell getprop ro.build.version.sdk | tr -d '\r')"

echo -e "\n=== Battery Info ==="
adb shell dumpsys battery | grep -E "level|status|health"

echo -e "\n=== Memory Info ==="
adb shell cat /proc/meminfo | head -n 3

echo -e "\n=== CPU Info ==="
adb shell cat /proc/cpuinfo | grep -E "Hardware|Processor|BogoMIPS|Features" | head -n 4
