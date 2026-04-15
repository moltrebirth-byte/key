#!/bin/bash

# Exit on error
set -e

echo "[*] Creating APE corpus directory..."
mkdir -p corpus_ape

# Generate a more complex APE file header including a dummy seek table and APEv2 tag
cat << 'EOF' > generate_ape_corpus.py
import struct

def create_ape_file(filename, frames, include_tag=False):
    # APEDescriptor (52 bytes)
    magic = b'MAC '
    version = struct.pack('<H', 3990)
    padding = struct.pack('<H', 0)
    desc_bytes = struct.pack('<I', 52)
    header_bytes = struct.pack('<I', 24)
    seek_bytes = struct.pack('<I', frames * 4) # 4 bytes per frame
    wav_head_bytes = struct.pack('<I', 44)
    audio_bytes = struct.pack('<I', 1024) # Dummy audio data size
    audio_bytes_high = struct.pack('<I', 0)
    wav_tail_bytes = struct.pack('<I', 0)
    md5 = b'\x00' * 16

    descriptor = magic + version + padding + desc_bytes + header_bytes + \
                 seek_bytes + wav_head_bytes + audio_bytes + audio_bytes_high + \
                 wav_tail_bytes + md5

    # APEHeader (24 bytes)
    comp_level = struct.pack('<H', 2000)
    flags = struct.pack('<H', 0)
    blocks_per_frame = struct.pack('<I', 73728)
    final_frame_blocks = struct.pack('<I', 1000)
    total_frames = struct.pack('<I', frames)
    bps = struct.pack('<H', 16)
    channels = struct.pack('<H', 2)
    sample_rate = struct.pack('<I', 44100)

    header = comp_level + flags + blocks_per_frame + final_frame_blocks + \
             total_frames + bps + channels + sample_rate

    # Dummy Seek Table
    seek_table = b''
    for i in range(frames):
        seek_table += struct.pack('<I', i * 1024) # Dummy offsets

    # Dummy Audio Data
    audio_data = b'\xAA' * 1024

    # APEv2 Tag
    tag_data = b''
    if include_tag:
        # Item: "Title" = "Fuzz"
        item_val = b'Fuzz'
        item_size = struct.pack('<I', len(item_val))
        item_flags = struct.pack('<I', 0)
        item_key = b'Title\x00'
        tag_item = item_size + item_flags + item_key + item_val

        # Footer (32 bytes)
        preamble = b'APETAGEX'
        tag_version = struct.pack('<I', 2000)
        tag_size = struct.pack('<I', 32 + len(tag_item))
        item_count = struct.pack('<I', 1)
        tag_flags = struct.pack('<I', 0) # Footer flag
        reserved = b'\x00' * 8
        
        tag_footer = preamble + tag_version + tag_size + item_count + tag_flags + reserved
        tag_data = tag_item + tag_footer

    with open(f'corpus_ape/{filename}', 'wb') as f:
        f.write(descriptor + header + seek_table + audio_data + tag_data)
    print(f"[+] Created corpus_ape/{filename}")

# Create variations for the corpus
create_ape_file('minimal.ape', frames=0, include_tag=False)
create_ape_file('with_seek.ape', frames=10, include_tag=False)
create_ape_file('with_tag.ape', frames=5, include_tag=True)

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