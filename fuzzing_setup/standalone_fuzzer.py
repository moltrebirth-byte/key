#!/usr/bin/env python3
import os
import random
import subprocess
import sys
import time
import argparse

# =========================================================================
# Standalone Fuzzer Demonstration Script - Generic Target Execution
# This script demonstrates how a fuzzer executes an arbitrary target
# program and monitors it for crashes.
# =========================================================================

CORPUS_DIR = "corpus_ape"
OUTPUT_DIR = "fuzz_output"
CRASH_DIR = "crashes"
ALL_MUTATIONS_DIR = "all_mutations"

def setup(target):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CRASH_DIR, exist_ok=True)
    os.makedirs(ALL_MUTATIONS_DIR, exist_ok=True)
    
    # If no target is specified, create and use the dummy target
    if not target:
        print("[*] No target specified. Creating dummy target...")
        with open("dummy_decoder.c", "w") as f:
            f.write("""
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    FILE *f = fopen(argv[1], "rb");
    if (!f) return 1;
    
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    rewind(f);
    
    unsigned char *buf = malloc(size);
    fread(buf, 1, size, f);
    fclose(f);
    
    // Simulate a crash based on a specific byte pattern
    if (size > 10 && buf[5] == 0xFF && buf[6] == 0xAA) {
        printf("CRASH TRIGGERED!\\n");
        int *p = NULL;
        *p = 42; // Segfault
    }
    
    free(buf);
    return 0;
}
            """)
        subprocess.run(["gcc", "dummy_decoder.c", "-o", "./dummy_decoder"])
        return "./dummy_decoder"
    return target

def mutate_structure_aware(data):
    mutated = bytearray(data)
    mutation_strategy = random.choice(["random", "target_descriptor", "target_header"])
    
    if mutation_strategy == "target_descriptor" and len(mutated) >= 52:
        offset = 6
        mutated[offset] = 0xFF
        mutated[offset+1] = 0xFF
        mutated[offset+2] = 0xFF
        mutated[offset+3] = 0xFF
    elif mutation_strategy == "target_header" and len(mutated) >= 76:
        offset = 56
        mutated[offset] = 0x00
        mutated[offset+1] = 0x00
        mutated[offset+2] = 0x00
        mutated[offset+3] = 0x00
    else:
        if len(mutated) > 0:
            idx = random.randint(0, len(mutated) - 1)
            mutated[idx] ^= (1 << random.randint(0, 7))
            
    return mutated, mutation_strategy

def fuzz(target_cmd, save_all=False):
    corpus_files = [os.path.join(CORPUS_DIR, f) for f in os.listdir(CORPUS_DIR) if os.path.isfile(os.path.join(CORPUS_DIR, f))]
    if not corpus_files:
        print("Error: Corpus directory is empty.")
        return

    print(f"[*] Starting fuzzer with {len(corpus_files)} corpus files...")
    print(f"[*] Target command: {target_cmd} <input_file>")
    
    iteration = 0
    crashes = 0
    stats = {
        "random": {"attempts": 0, "crashes": 0},
        "target_descriptor": {"attempts": 0, "crashes": 0},
        "target_header": {"attempts": 0, "crashes": 0}
    }
    
    try:
        while True:
            iteration += 1
            
            seed_file = random.choice(corpus_files)
            with open(seed_file, "rb") as f:
                seed_data = f.read()
                
            mutated_data, strategy = mutate_structure_aware(seed_data)
            stats[strategy]["attempts"] += 1
            
            test_file = os.path.join(OUTPUT_DIR, f"test_{iteration}.ape")
            with open(test_file, "wb") as f:
                f.write(mutated_data)
                
            if save_all:
                save_file = os.path.join(ALL_MUTATIONS_DIR, f"mutated_{iteration}_{strategy}.ape")
                with open(save_file, "wb") as f:
                    f.write(mutated_data)
                
            try:
                # Execute the target command with the test file as an argument
                # e.g., if target_cmd is "ffmpeg -i", it runs "ffmpeg -i test_1.ape"
                cmd = target_cmd.split() + [test_file]
                
                # Capture stdout and stderr for logging
                result = subprocess.run(cmd, capture_output=True, timeout=2)
                
                # Check for crashes. Return codes like -11 (SIGSEGV) or -6 (SIGABRT) indicate crashes on POSIX.
                # A non-zero return code might just be a parsing error, but we log it as a potential issue.
                if result.returncode < 0 or result.returncode > 127: # Typical range for fatal signals
                    crashes += 1
                    stats[strategy]["crashes"] += 1
                    
                    crash_file = os.path.join(CRASH_DIR, f"crash_{iteration}_{strategy}_sig{result.returncode}.ape")
                    os.rename(test_file, crash_file)
                    
                    # Log the crash details
                    log_file = os.path.join(CRASH_DIR, f"crash_{iteration}_{strategy}_sig{result.returncode}.log")
                    with open(log_file, "w") as log:
                        log.write(f"Command: {' '.join(cmd)}\\n")
                        log.write(f"Return Code: {result.returncode}\\n")
                        log.write(f"--- STDOUT ---\\n{result.stdout.decode('utf-8', errors='ignore')}\\n")
                        log.write(f"--- STDERR ---\\n{result.stderr.decode('utf-8', errors='ignore')}\\n")
                        
                    print(f"[!] Crash found! Strategy: {strategy} | Return Code: {result.returncode} | Saved to {crash_file}")
                else:
                    os.remove(test_file)
                    
            except subprocess.TimeoutExpired:
                print(f"[-] Timeout on iteration {iteration}")
                os.remove(test_file)
            except Exception as e:
                print(f"[-] Execution error: {e}")
                os.remove(test_file)
                
            if iteration % 100 == 0:
                print(f"[*] Iterations: {iteration} | Crashes: {crashes}")
                
    except KeyboardInterrupt:
        print("\n[*] Fuzzing stopped by user.")
        print(f"[*] Total Iterations: {iteration} | Total Crashes: {crashes}")
        print("\n[*] Mutation Strategy Effectiveness:")
        for strat, data in stats.items():
            if data["attempts"] > 0:
                success_rate = (data["crashes"] / data["attempts"]) * 100
                print(f"  - {strat}: {data['crashes']} crashes / {data['attempts']} attempts ({success_rate:.2f}%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Fuzzer Demonstration")
    parser.add_argument("-t", "--target", help="Command line target (e.g., 'ffmpeg -i'). If not provided, uses a dummy target.", default="")
    parser.add_argument("-s", "--save-all", action="store_true", help="Save all mutated files, not just crashes.")
    args = parser.parse_args()

    if not os.path.exists(CORPUS_DIR):
        print(f"Error: Corpus directory '{CORPUS_DIR}' not found. Run the setup script first.")
        sys.exit(1)
        
    actual_target = setup(args.target)
    fuzz(actual_target, args.save_all)