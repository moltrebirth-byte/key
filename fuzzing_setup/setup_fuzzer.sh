#!/bin/bash

# Exit on error
set -e

echo "[*] Setting up libFuzzer environment..."

# 1. Install dependencies (Assuming Debian/Ubuntu based Linux environment)
echo "[*] Installing Clang and LLVM..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y clang llvm
else
    echo "[!] apt-get not found. Please install clang and llvm manually."
fi

# 2. Create a corpus directory
# The corpus is a set of valid input files the fuzzer uses as a starting point for mutations.
echo "[*] Creating initial corpus directory..."
mkdir -p corpus
mkdir -p crashes

# Create a dummy valid file to start the fuzzer
echo -n "RIFF" > corpus/dummy.wav
echo -n "ID3" > corpus/dummy.mp3

# 3. Compile the harness
# -g: Include debug symbols (crucial for ASan stack traces)
# -O1: Basic optimization
# -fsanitize=fuzzer: Links the libFuzzer engine
# -fsanitize=address: Enables AddressSanitizer to catch memory corruption (UAF, buffer overflows, etc.)
echo "[*] Compiling the harness with ASan and libFuzzer..."
clang++ -g -O1 -fsanitize=fuzzer,address fuzz_harness.cpp -o audio_fuzzer

echo "[+] Compilation complete."
echo ""
echo "================================================================"
echo "To run the fuzzer, execute:"
echo "  ./audio_fuzzer -max_total_time=60 -artifact_prefix=crashes/ corpus/"
echo "================================================================"