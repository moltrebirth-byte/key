#!/bin/bash

# Exit on error
set -e

echo "[*] Creating APE corpus directory..."
mkdir -p corpus_ape

# Generate a minimal, structurally valid APE file header.
# This gives the fuzzer a valid starting point so it doesn't waste time 
# guessing the "MAC " magic bytes and basic structure.

# We will use python to write specific bytes
cat << 'EOF' > generate_ape_corpus.py
import struct

# APEDescriptor (52 bytes)
magic = b'MAC '
version = struct.pack('<H', 3990) # v3.99
padding = struct.pack('<H', 0)
desc_bytes = struct.pack('<I', 52)
header_bytes = struct.pack('<I', 24)
seek_bytes = struct.pack('<I', 0)
wav_head_bytes = struct.pack('<I', 44)
audio_bytes = struct.pack('<I', 0)
audio_bytes_high = struct.pack('<I', 0)
wav_tail_bytes = struct.pack('<I', 0)
md5 = b'\x00' * 16

descriptor = magic + version + padding + desc_bytes + header_bytes + \
             seek_bytes + wav_head_bytes + audio_bytes + audio_bytes_high + \
             wav_tail_bytes + md5

# APEHeader (24 bytes)
comp_level = struct.pack('<H', 2000) # Normal
flags = struct.pack('<H', 0)
blocks_per_frame = struct.pack('<I', 73728)
final_frame_blocks = struct.pack('<I', 0)
total_frames = struct.pack('<I', 0)
bps = struct.pack('<H', 16)
channels = struct.pack('<H', 2)
sample_rate = struct.pack('<I', 44100)

header = comp_level + flags + blocks_per_frame + final_frame_blocks + \
         total_frames + bps + channels + sample_rate

with open('corpus_ape/minimal.ape', 'wb') as f:
    f.write(descriptor + header)

print("[+] Created corpus_ape/minimal.ape")
EOF

python3 generate_ape_corpus.py
rm generate_ape_corpus.py

# Compile the new harness
echo "[*] Compiling APE harness with ASan and libFuzzer..."
clang++ -g -O1 -fsanitize=fuzzer,address ape_harness.cpp -o ape_fuzzer

echo "[+] Compilation complete."
echo ""
echo "================================================================"
echo "To run the APE fuzzer, execute:"
echo "  ./ape_fuzzer -max_total_time=60 -artifact_prefix=crashes/ corpus_ape/"
echo "================================================================"