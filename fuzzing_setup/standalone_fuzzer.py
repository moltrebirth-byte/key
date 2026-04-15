#!/usr/bin/env python3
import os
import random
import subprocess
import sys
import time

# =========================================================================
# Standalone Fuzzer Demonstration Script
# This script demonstrates the mechanics of mutation-based fuzzing.
# It generates malformed files by applying random mutations to a valid corpus
# and feeds them to a DUMMY target program.
# It DOES NOT include an actual APE decoder or target any real software.
# =========================================================================

CORPUS_DIR = "corpus_ape"
OUTPUT_DIR = "fuzz_output"
CRASH_DIR = "crashes"
DUMMY_TARGET = "./dummy_decoder"

def setup():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CRASH_DIR, exist_ok=True)
    
    # Create a dummy target program that crashes randomly for demonstration
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
    subprocess.run(["gcc", "dummy_decoder.c", "-o", DUMMY_TARGET])

def mutate(data):
    """Applies random mutations to a byte array."""
    mutated = bytearray(data)
    num_mutations = random.randint(1, 5)
    
    for _ in range(num_mutations):
        mutation_type = random.choice(["bitflip", "byte_overwrite", "magic_value"])
        
        if len(mutated) == 0:
            continue
            
        idx = random.randint(0, len(mutated) - 1)
        
        if mutation_type == "bitflip":
            bit = 1 << random.randint(0, 7)
            mutated[idx] ^= bit
        elif mutation_type == "byte_overwrite":
            mutated[idx] = random.randint(0, 255)
        elif mutation_type == "magic_value":
            # Insert potentially problematic values (e.g., max int, negative numbers)
            magic_vals = [0xFF, 0x00, 0x7F, 0x80]
            mutated[idx] = random.choice(magic_vals)
            
    return mutated

def fuzz():
    corpus_files = [os.path.join(CORPUS_DIR, f) for f in os.listdir(CORPUS_DIR) if os.path.isfile(os.path.join(CORPUS_DIR, f))]
    if not corpus_files:
        print("Error: Corpus directory is empty.")
        return

    print(f"[*] Starting fuzzer with {len(corpus_files)} corpus files...")
    iteration = 0
    crashes = 0
    
    try:
        while True:
            iteration += 1
            
            # 1. Select a random file from the corpus
            seed_file = random.choice(corpus_files)
            with open(seed_file, "rb") as f:
                seed_data = f.read()
                
            # 2. Mutate the data
            mutated_data = mutate(seed_data)
            
            # 3. Write the mutated data to a temporary file
            test_file = os.path.join(OUTPUT_DIR, f"test_{iteration}.ape")
            with open(test_file, "wb") as f:
                f.write(mutated_data)
                
            # 4. Execute the target program with the mutated file
            try:
                # We use a timeout to catch infinite loops
                result = subprocess.run([DUMMY_TARGET, test_file], capture_output=True, timeout=2)
                
                # 5. Check for crashes (return code != 0 usually indicates a crash like SIGSEGV)
                if result.returncode != 0:
                    crashes += 1
                    crash_file = os.path.join(CRASH_DIR, f"crash_{iteration}_{result.returncode}.ape")
                    os.rename(test_file, crash_file)
                    print(f"[!] Crash found! Saved to {crash_file}")
                else:
                    # If it didn't crash, we don't need the test file
                    os.remove(test_file)
                    
            except subprocess.TimeoutExpired:
                print(f"[-] Timeout on iteration {iteration}")
                os.remove(test_file)
                
            if iteration % 100 == 0:
                print(f"[*] Iterations: {iteration} | Crashes: {crashes}")
                
    except KeyboardInterrupt:
        print("\n[*] Fuzzing stopped by user.")
        print(f"[*] Total Iterations: {iteration} | Total Crashes: {crashes}")

if __name__ == "__main__":
    if not os.path.exists(CORPUS_DIR):
        print(f"Error: Corpus directory '{CORPUS_DIR}' not found. Run the setup script first.")
        sys.exit(1)
        
    setup()
    fuzz()