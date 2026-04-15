# Android Testing Toolkit

A small, safe toolkit for Android development and QA workflows using **ADB**. It helps automate repetitive local tasks during app testing without remote control, persistence tricks, or background command channels.

## Features

- Capture screenshots from a connected test device
- Pull and save logcat output
- Install or reinstall debug/test APKs
- Collect basic device information
- Run repeatable local test helper commands

## Requirements

- Android SDK Platform Tools
- `adb` available in your PATH
- USB debugging enabled on the test device
- A connected authorized Android device or emulator

## Quick Start

```bash
git clone https://github.com/moltrebirth-byte/key.git
cd key
chmod +x scripts/*.sh
./scripts/device-info.sh
./scripts/capture-screenshot.sh
./scripts/pull-logs.sh
```

## Available Scripts

### 1. Device Info
Prints connected device details.

```bash
./scripts/device-info.sh
```

### 2. Capture Screenshot
Captures a screenshot on the device and pulls it locally into `output/screenshots/`.

```bash
./scripts/capture-screenshot.sh
```

### 3. Pull Logs
Collects a timestamped `logcat` dump into `output/logs/`.

```bash
./scripts/pull-logs.sh
```

### 4. Install APK
Installs a provided APK on the connected device.

```bash
./scripts/install-apk.sh path/to/app-debug.apk
```

## Directory Layout

```text
key/
├── README.md
├── scripts/
│   ├── device-info.sh
│   ├── capture-screenshot.sh
│   ├── pull-logs.sh
│   └── install-apk.sh
└── output/
    ├── logs/
    └── screenshots/
```

## Notes

This repository is intended for **local development and QA support** only. All actions are initiated directly by the developer on their own machine against their own test device or emulator.
