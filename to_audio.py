#!/usr/bin/env python3

import os
import subprocess

def main():
    print("[*] Starting APE to audio conversion automation...")

    # 1. Look for all .ape files in ./output/
    input_dir = "./output"
    if not os.path.exists(input_dir):
        print(f[!z] Error: Input directory {input_dir} not found.")
        return

    ape_files = [f for f in os.listdir(input_dir) if f.endswith(".ape")]

    if not ape_files:
        print(f[!z] No .ape files found in {input_dir}.")
        return

    print(f"[*] Found {len(ape_files)} .ape files.")

    # 2. Run the existing audio converter on each one
    # 3. Save the converted audio files to ./final_audio/
    output_dir = "./final_audio"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    converted_files = []
    for ape_file in ape_files:
        ape_path = os.path.join(input_dir, ape_file)
        wav_file = ape_file.replace(".ape", ".wav")
        wav_path = os.path.join(output_dir, wav_file)

        print(f[*] Converting {ape_file} to {wav_file}...")
        try:
            subprocess.run(["python", "ape_to_audio.py", ape_path, wav_path], check=True)
            converted_files.append(wav_file)
        except subprocess.CalledProcessError as e:
            print(f[!] Error converting {ape_file}: {e}")
        except FileNotFoundError:
            print("[!] Error: 'python' command or 'ape_to_audio.py' not found.")
            return

    # 4. Create a simple text report listing all audio files created
    report_path = os.path.join(output_dir, "audio_report.txt")
    try:
        with open(report_path, "w") as f:
            f.write("Audio Files Generated:\n")
            f.write("=" * 20 + "\n")
            for file in converted_files:
                f.write(f{file}\n")
        print(f[*] Created report at {report_path}")
    except Exception as e:
        print("[!] Error creating report: {}".format(e))

    print("[+] All done, Jack.")

if __name__ == "__main__":
    main()