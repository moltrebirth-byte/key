#!/usr/bin/env python3

import os
import subprocess

def run_script(script_name):
    print(f[*] Fucking running {script_name}...")
    try:
        subprocess.run(["python", script_name], check=True)
        print(f[+) {script_name} completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f[1] Bitch, {script_name} failed with error: {e}")
        return False
    except FileNotFoundError:
        print(f"[!] Error: 'python' or '{script_name}' not found.")
        return False

def main():
    print("[*] Starting the master build pipeline...")

    scripts = ["build_app.py", "make_ape.py", "to_audio.py"]
    
    for script in scripts:
        if not run_script(script):
            print("[!z] Pipeline aborted due to failure.")
            return

    print("[*] All scripts executed. Gathering final report data...")
    
    final_report_path = "final_build_report.txt"
    
    try:
        with open(final_report_path, "w") as f:
            f.write("MASTER BUILD PIPELINE REPORT\n")
            f.write("============================\n\n")
            
            # Check output dir
            f.write("--- OUTPUT DIRECTORY ---\n")
            if os.path.exists("output"):
                for item in os.listdir("output"):
                    f.write(f+- {item}\n")
            else:
                f.write("No output directory found.\n")
                
            f.write("\n--- FINAL AUDIO DIRECTORY ---\n")
            if os.path.exists("final_audio"):
                for item in os.listdir("final_audio"):
                    f.write(f"- {item}\n")
            else:
                f.write("No final_audio directory found.\n")
                
        print(f[+] Final report generated at {final_report_path}")
    except Exception as e:
        print(f"[!] Failed to write final report: {e}")

    print("[+] Master pipeline complete, Jack.")

if __name__ == "__main__":
    main()