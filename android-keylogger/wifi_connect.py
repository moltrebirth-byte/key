#!/usr/bin/env python3
"""
wifi_connect.py — ADB-over-WiFi auto-connect + reconnect-on-drop

Features:
  - Auto-enable ADB TCP mode via USB (if device is connected via USB first)
  - Connect to device over WiFi by IP (auto-detect or manual)
  - Heartbeat thread: pings device every N seconds
  - On drop: exponential backoff reconnect loop
  - On reconnect: fires a user-supplied callback (e.g. restart keylogger)
  - Can be used standalone or imported as a module

Usage (standalone):
  python wifi_connect.py --ip 192.168.1.100 --port 5555 --on-connect "./deploy.sh"

Usage (as module):
  from wifi_connect import ADBWifiManager
  mgr = ADBWifiManager(ip="192.168.1.100", port=5555)
  mgr.on_reconnect = lambda: restart_keylogger()
  mgr.start()   # blocks — run in a thread if needed
"""

import subprocess
import threading
import time
import argparse
import sys
import os
import socket
from typing import Optional, Callable

# ── Constants ────────────────────────────────────────────────
DEFAULT_PORT      = 5555
HEARTBEAT_INTERVAL = 5      # seconds between liveness checks
RECONNECT_BASE    = 2       # base backoff seconds
RECONNECT_MAX     = 60      # max backoff cap
RECONNECT_FACTOR  = 2       # exponential multiplier
ADB_TIMEOUT       = 8       # seconds for adb subprocess calls


def _run(*args, timeout: int = ADB_TIMEOUT) -> subprocess.CompletedProcess:
    """Run a command, return CompletedProcess. Never raises on non-zero exit."""
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout
    )


def _adb(*args, serial: str = "", timeout: int = ADB_TIMEOUT) -> subprocess.CompletedProcess:
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    return _run(*cmd, timeout=timeout)


def get_usb_devices() -> list[str]:
    """Return list of currently connected USB ADB device serials."""
    r = _run("adb", "devices")
    devices = []
    for line in r.stdout.splitlines()[1:]:
        line = line.strip()
        if line and "\t" in line:
            serial, state = line.split("\t", 1)
            if state.strip() == "device" and ":" not in serial:  # exclude TCP
                devices.append(serial.strip())
    return devices


def get_device_wifi_ip(serial: str = "") -> Optional[str]:
    """
    Try to get the device's WiFi IP via:
      1. ip addr show wlan0
      2. ifconfig wlan0
      3. getprop dhcp.wlan0.ipaddress
    Returns IP string or None.
    """
    cmds = [
        ["shell", "ip", "-f", "inet", "addr", "show", "wlan0"],
        ["shell", "ifconfig", "wlan0"],
        ["shell", "getprop", "dhcp.wlan0.ipaddress"],
    ]
    for cmd in cmds:
        r = _adb(*cmd, serial=serial)
        out = r.stdout.strip()
        if not out:
            continue
        # Parse "inet x.x.x.x" or "addr:x.x.x.x"
        for token in out.split():
            token = token.strip().rstrip("/")
            # strip prefix length if present (e.g. "192.168.1.5/24")
            ip = token.split("/")[0]
            try:
                socket.inet_aton(ip)
                if not ip.startswith("127.") and not ip.startswith("0."):
                    return ip
            except socket.error:
                continue
    return None


def enable_tcpip(serial: str = "", port: int = DEFAULT_PORT) -> bool:
    """Switch device to TCP/IP mode on given port (requires USB connection)."""
    r = _adb("tcpip", str(port), serial=serial)
    ok = r.returncode == 0 or "restarting" in r.stdout.lower()
    return ok


def adb_connect(ip: str, port: int = DEFAULT_PORT) -> bool:
    """Run 'adb connect ip:port', return True on success."""
    target = f"{ip}:{port}"
    r = _run("adb", "connect", target)
    out = (r.stdout + r.stderr).lower()
    return "connected" in out and "unable" not in out and "failed" not in out


def adb_disconnect(ip: str, port: int = DEFAULT_PORT):
    target = f"{ip}:{port}"
    _run("adb", "disconnect", target)


def is_device_alive(serial: str) -> bool:
    """
    Liveness check: run 'adb -s serial shell echo ok'
    Returns True if device responds within ADB_TIMEOUT.
    """
    try:
        r = _adb("shell", "echo", "__alive__", serial=serial, timeout=ADB_TIMEOUT)
        return "__alive__" in r.stdout
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


class ADBWifiManager:
    """
    Manages ADB-over-WiFi connection to a single Android device.

    Lifecycle:
      start()  →  connect loop  →  heartbeat thread
                                        ↓ drop detected
                                   reconnect loop (exponential backoff)
                                        ↓ reconnected
                                   on_reconnect() callback
                                        ↓
                                   heartbeat resumes
    """

    def __init__(
        self,
        ip: str,
        port: int = DEFAULT_PORT,
        heartbeat_interval: int = HEARTBEAT_INTERVAL,
        on_reconnect: Optional[Callable] = None,
        verbose: bool = True,
    ):
        self.ip                 = ip
        self.port               = port
        self.serial             = f"{ip}:{port}"
        self.heartbeat_interval = heartbeat_interval
        self.on_reconnect       = on_reconnect  # called after every successful reconnect
        self.verbose            = verbose

        self._stop_event   = threading.Event()
        self._hb_thread: Optional[threading.Thread] = None
        self._connected    = False
        self._reconnect_cb_fired_on_first = False

    # ── Logging ──────────────────────────────────────────────
    def _log(self, msg: str):
        if self.verbose:
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] [ADBWifi] {msg}", flush=True)

    # ── Connect / reconnect ──────────────────────────────────
    def _try_connect(self) -> bool:
        self._log(f"Connecting to {self.serial}...")
        ok = adb_connect(self.ip, self.port)
        if ok:
            self._log(f"Connected: {self.serial}")
            self._connected = True
        else:
            self._log(f"Connect failed: {self.serial}")
            self._connected = False
        return ok

    def _reconnect_loop(self):
        """Exponential backoff reconnect. Blocks until connected or stop requested."""
        backoff = RECONNECT_BASE
        attempt = 0
        while not self._stop_event.is_set():
            attempt += 1
            self._log(f"Reconnect attempt #{attempt} (backoff {backoff}s)...")
            if self._try_connect():
                if self.on_reconnect:
                    self._log("Firing on_reconnect callback...")
                    try:
                        self.on_reconnect()
                    except Exception as e:
                        self._log(f"on_reconnect raised: {e}")
                backoff = RECONNECT_BASE  # reset backoff on success
                return
            self._log(f"Waiting {backoff}s before next attempt...")
            self._stop_event.wait(timeout=backoff)
            backoff = min(backoff * RECONNECT_FACTOR, RECONNECT_MAX)

    # ── Heartbeat ────────────────────────────────────────────
    def _heartbeat(self):
        """Runs in a thread. Checks device liveness every heartbeat_interval seconds."""
        self._log(f"Heartbeat started (interval={self.heartbeat_interval}s)")
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.heartbeat_interval)
            if self._stop_event.is_set():
                break
            if not is_device_alive(self.serial):
                self._log(f"Device {self.serial} dropped! Starting reconnect loop...")
                self._connected = False
                self._reconnect_loop()
            else:
                self._log(f"Heartbeat OK: {self.serial}")
        self._log("Heartbeat thread exiting.")

    # ── Public API ───────────────────────────────────────────
    def start(self, block: bool = True):
        """
        Connect and start heartbeat.
        block=True: runs heartbeat on calling thread (use in a dedicated thread).
        block=False: starts heartbeat as a daemon thread and returns immediately.
        """
        # Initial connect with reconnect loop
        if not self._try_connect():
            self._reconnect_loop()

        if self._stop_event.is_set():
            return  # stop was called during reconnect

        self._hb_thread = threading.Thread(
            target=self._heartbeat,
            daemon=True,
            name="adb-wifi-heartbeat"
        )
        if block:
            self._heartbeat()  # run on caller thread
        else:
            self._hb_thread.start()

    def stop(self):
        """Signal stop and disconnect."""
        self._log("Stopping...")
        self._stop_event.set()
        adb_disconnect(self.ip, self.port)
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected


# ── Auto-setup helper ────────────────────────────────────────
def auto_setup_wifi(
    port: int = DEFAULT_PORT,
    usb_serial: str = "",
) -> Optional[str]:
    """
    Full auto-setup:
      1. Find USB-connected device
      2. Get its WiFi IP
      3. Enable TCP/IP mode
      4. Connect over WiFi
    Returns the IP on success, None on failure.
    """
    print("[*] Auto-setup: looking for USB-connected device...")

    if usb_serial:
        serials = [usb_serial]
    else:
        serials = get_usb_devices()

    if not serials:
        print("[-] No USB devices found. Connect via USB first.")
        return None

    serial = serials[0]
    print(f"[+] Found USB device: {serial}")

    ip = get_device_wifi_ip(serial)
    if not ip:
        print("[-] Could not get WiFi IP. Is WiFi enabled on device?")
        return None
    print(f"[+] Device WiFi IP: {ip}")

    print(f"[*] Enabling TCP/IP on port {port}...")
    if not enable_tcpip(serial, port):
        print("[-] Failed to enable TCP/IP mode.")
        return None

    # Give device a moment to restart ADB daemon in TCP mode
    time.sleep(2)

    print(f"[*] Connecting over WiFi to {ip}:{port}...")
    if adb_connect(ip, port):
        print(f"[+] WiFi ADB connected: {ip}:{port}")
        print("[*] You can now unplug USB.")
        return ip
    else:
        print(f"[-] WiFi connect failed to {ip}:{port}")
        return None


# ── CLI entry point ──────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="ADB-over-WiFi auto-connect + reconnect-on-drop manager"
    )
    parser.add_argument("--ip",          default="",              help="Device IP (skip for auto-detect via USB)")
    parser.add_argument("--port",        default=DEFAULT_PORT,    type=int, help="ADB TCP port (default 5555)")
    parser.add_argument("--usb-serial",  default="",              help="USB serial to use for auto-setup")
    parser.add_argument("--heartbeat",   default=HEARTBEAT_INTERVAL, type=int, help="Heartbeat interval in seconds")
    parser.add_argument("--on-connect",  default="",              help="Shell command to run on (re)connect")
    parser.add_argument("--auto-setup",  action="store_true",     help="Auto-detect IP and enable TCP/IP via USB")
    args = parser.parse_args()

    ip = args.ip

    if args.auto_setup or not ip:
        ip = auto_setup_wifi(port=args.port, usb_serial=args.usb_serial)
        if not ip:
            sys.exit(1)

    on_reconnect_cb = None
    if args.on_connect:
        cmd = args.on_connect
        def on_reconnect_cb():
            print(f"[*] Running on-connect command: {cmd}")
            os.system(cmd)

    mgr = ADBWifiManager(
        ip=ip,
        port=args.port,
        heartbeat_interval=args.heartbeat,
        on_reconnect=on_reconnect_cb,
        verbose=True,
    )

    print(f"[*] Managing {ip}:{args.port} | heartbeat every {args.heartbeat}s")
    print("[*] Ctrl+C to stop.\n")

    try:
        mgr.start(block=True)
    except KeyboardInterrupt:
        print("\n[*] Interrupted.")
        mgr.stop()


if __name__ == "__main__":
    main()
