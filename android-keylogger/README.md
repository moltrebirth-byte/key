# Android Keylogger (ADB-based)

Monitors raw Linux input events on an Android device via ADB and logs all key presses.

## How it works

- Connects to the device via `adb shell`
- Streams raw bytes from `/dev/input/eventX`
- Decodes `input_event` structs (supports both 32-bit and 64-bit Android)
- Filters `EV_KEY` events and maps keycodes to characters
- Writes timestamped log entries to a file

## Requirements

- Python 3.10+
- `adb` in PATH
- USB debugging enabled on target device (or ADB over TCP/IP)
- Device must allow reading `/dev/input/eventX` (root helps, but some devices expose it without root)

## Usage

```bash
# Auto-detect event node, log to keylog.txt
python keylogger.py

# Specific device serial + specific event node
python keylogger.py --serial emulator-5554 --event event1 --out /tmp/keys.txt

# ADB over TCP (wireless)
adb connect 192.168.1.100:5555
python keylogger.py --serial 192.168.1.100:5555
```

## Arguments

| Argument   | Default      | Description                              |
|------------|--------------|------------------------------------------|
| `--serial` | *(empty)*    | ADB device serial. Omit for single device|
| `--event`  | *(auto)*     | Input event node (e.g. `event1`)         |
| `--out`    | `keylog.txt` | Output log file path                     |

## Finding the right event node

```bash
adb shell cat /proc/bus/input/devices
```

Look for a device with `EV=` bitmask that has bit 1 set (keyboard). The script auto-detects this.

## Output format

```
=== Session start: 2026-04-15T13:00:00.000 ===
[13:00:01.123] h
[13:00:01.210] e
[13:00:01.305] l
[13:00:01.401] l
[13:00:01.498] o
[13:00:01.600] [SPACE]
=== Session end: 2026-04-15T13:05:00.000 ===
```
