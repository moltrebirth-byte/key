#!/usr/bin/env python3
import os
import random
import subprocess
import sys
import time

# =========================================================================
# Standalone Fuzzer Demonstration Script - Structure-Aware Concepts
# This script demonstrates how a fuzzer might apply mutations to specific
# structural elements of a file format (like APE).
# It DOES NOT target an actual decoder (MAC or libape). It still uses the
# dummy target for demonstration purposes.
# =========================================================================

CORPUS_DIR = "corpus_ape"
OUTPUT_DIR = "fuzz_output"
CRASH_DIR = "crashes"
DUMMY_TARGET = "./dummy_decoder"

def setup():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CRASH_DIR, exist_ok=True)
    
    # Dummy target program
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

def mutate_structure_aware(data):
    """
    Demonstrates structure-aware mutations.
    Instead of randomly flipping bits anywhere, it targets specific offsets
    known to correspond to structural fields (e.g., in an APE header).
    """
    mutated = bytearray(data)
    
    # APE Descriptor is typically 52 bytes.
    # APE Header follows immediately after.
    
    mutation_strategy = random.choice(["random", "target_descriptor", "target_header"])
    
    if mutation_strategy == "target_descriptor" and len(mutated) >= 52:
        # Target the descriptorBytes field (offset 6, 4 bytes)
        # Mutating size fields often leads to integer overflows or OOB reads
        offset = 6
        mutated[offset] = 0xFF
        mutated[offset+1] = 0xFF
        mutated[offset+2] = 0xFF
        mutated[offset+3] = 0xFF # Set to max uint32
        
    elif mutation_strategy == "target_header" and len(mutated) >= 76:
        # Target the blocksPerFrame field in the header (offset 52 + 4 = 56, 4 bytes)
        offset = 56
        # Insert a negative value or 0 to test divide-by-zero or allocation logic
        mutated[offset] = 0x00
        mutated[offset+1] = 0x00
        mutated[offset+2] = 0x00
        mutated[offset+3] = 0x00
        
    else:
        # Fallback to random mutation
        if len(mutated) > 0:
            idx = random.randint(0, len(mutated) - 1)
            mutated[idx] ^= (1 << random.randint(0, 7))
            
    return mutated, mutation_strategy

def fuzz():
    corpus_files = [os.path.join(CORPUS_DIR, f) for f in os.listdir(CORPUS_DIR) if os.path.isfile(os.path.join(CORPUS_DIR, f))]
    if not corpus_files:
        print("Error: Corpus directory is empty.")
        return

    print(f"[*] Starting fuzzer with {len(corpus_files)} corpus files...")
    iteration = 0
    crashes = 0
    
    # Basic statistics tracking
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
                
            try:
                result = subprocess.run([DUMMY_TARGET, test_file], capture_output=True, timeout=2)
                
                if result.returncode != 0:
                    crashes += 1
                    stats[strategy]["crashes"] += 1
                    crash_file = os.path.join(CRASH_DIR, f"crash_{iteration}_{strategy}.ape")
                    os.rename(test_file, crash_file)
                    print(f"[!] Crash found! Strategy: {strategy} | Saved to {crash_file}")
                else:
                    os.remove(test_file)
                    
            except subprocess.TimeoutExpired:
                print(f"[-] Timeout on iteration {iteration}")
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
    if not os.path.exists(CORPUS_DIR):
        print(f"Error: Corpus directory '{CORPUS_DIR}' not found. Run the setup script first.")
        sys.exit(1)
        
    setup()
    fuzz()