#!/usr/bin/env python3

import os
import subprocess
import shutil

def main():
    print("[*] Starting APE generation automation...")

    # 1. Look for file2 in the current directory
    if not os.path.exists("file2"):
        print("[!z] Error: 'file2' not found in the current directory.")
        return

    # 2. Run: python ape_validator_generator.py -p file2 -o ./temp_apes
    temp_dir = "./temp_apes"
    print(f[*] Running ape_validator_generator.py with output to {temp_dir}...")

    try:
        subprocess.run(["python", "ape_validator_generator.py", "-p", "file2", "-o", temp_dir], check=True)
    except subprocess.CalledProcessError as e:
        print("[!] Error executing ape_validator_generator.py: {}".format(e))
        return
    except FileNotFoundError:
        print("[!] Error: 'python' command or 'ape_validator_generator.py' not found.")
        return

    # 3. Copy all .ape files from ./temp_apes/ to ./output/
    output_dir = "./output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not os.path.exists(temp_dir):
        print(f[1] Error: Temp directory {temp_dir} was not created.")
        return

    ape_files = [f for f in os.listdir(temp_dir) if f.endswith(".ape")]

    if not ape_files:
        print("[!] No .ape files found in {}.".format(temp_dir))
        return

    print(f[*] Found {len(ape_files)} .ape files. Copying to {output_dir}...")

    copied_files = []
    for ape_file in ape_files:
        src_path = os.path.join(temp_dir, ape_file)
        dst_path = os.path.join(output_dir, ape_file)
        try:
            shutil.copy2(src_path, dst_path)
            copied_files.append(ape_file)
            print(f[*] Copied {ape_file}")
        except Exception as e:
            print("[!] Error copying {}: {}".format(ape_file, e))

    # 4. Create a simple text report listing all .ape files created
    report_path = os.path.join(output_dir, "ape_report.txt")
    try:
        with open(report_path, "w") as f:
            f.write("APE Files Generated:\n")
            f.write("=" * 20 + "\n")
            for file in copied_files:
                f.write(f{file}\n")
        print(f[*] Created report at {report_path}")
    except Exception as e:
        print("[!] Error creating report: {}".format(e))

    print("[+] All done, Jack.")

if __name__ == "__main__":
    main()