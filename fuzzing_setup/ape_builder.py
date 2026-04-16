#!/usr/bin/env python3
import struct
import sys
import argparse

# =========================================================================
# Conceptual APE Format Builder
# This script demonstrates how to programmatically construct the structural
# elements of a Monkey's Audio (APE) file.
# It DOES NOT create an exploit payload or target any specific CVE.
# =========================================================================

def build_ape_file(output_filename, frames=10, inject_data=None, inject_offset="audio"):
    """
    Constructs an APE file, optionally injecting arbitrary data into
    specific structural locations for testing parser robustness.
    """
    print(f"[*] Building APE file: {output_filename}")
    
    # 1. APEDescriptor (52 bytes)
    magic = b'MAC '
    version = struct.pack('<H', 3990)
    padding = struct.pack('<H', 0)
    desc_bytes = struct.pack('<I', 52)
    header_bytes = struct.pack('<I', 24)
    seek_bytes = struct.pack('<I', frames * 4)
    wav_head_bytes = struct.pack('<I', 44)
    
    # Base audio size
    audio_size = 1024
    if inject_data and inject_offset == "audio":
        audio_size += len(inject_data)
        
    audio_bytes_field = struct.pack('<I', audio_size)
    audio_bytes_high = struct.pack('<I', 0)
    wav_tail_bytes = struct.pack('<I', 0)
    md5 = b'\x00' * 16

    descriptor = magic + version + padding + desc_bytes + header_bytes + \
                 seek_bytes + wav_head_bytes + audio_bytes_field + audio_bytes_high + \
                 wav_tail_bytes + md5

    # 2. APEHeader (24 bytes)
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

    # 3. Seek Table
    seek_table = b''
    for i in range(frames):
        seek_table += struct.pack('<I', i * 1024)

    # 4. Audio Data
    audio_data = b'\xAA' * 1024
    if inject_data and inject_offset == "audio":
        print(f"[*] Injecting {len(inject_data)} bytes into audio chunk...")
        audio_data += inject_data

    # 5. APEv2 Tag (Optional, but good for structure testing)
    tag_data = b''
    if inject_data and inject_offset == "tag":
        print(f"[*] Injecting {len(inject_data)} bytes into APEv2 tag...")
        item_val = inject_data
        item_size = struct.pack('<I', len(item_val))
        item_flags = struct.pack('<I', 0)
        item_key = b'TestPayload\x00'
        tag_item = item_size + item_flags + item_key + item_val

        preamble = b'APETAGEX'
        tag_version = struct.pack('<I', 2000)
        tag_size = struct.pack('<I', 32 + len(tag_item))
        item_count = struct.pack('<I', 1)
        tag_flags = struct.pack('<I', 0)
        reserved = b'\x00' * 8
        
        tag_footer = preamble + tag_version + tag_size + item_count + tag_flags + reserved
        tag_data = tag_item + tag_footer

    # Assemble the final file
    with open(output_filename, 'wb') as f:
        f.write(descriptor + header + seek_table + audio_data + tag_data)
        
    print("[+] Build complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Conceptual APE Format Builder")
    parser.add_argument("-o", "--output", default="test_build.ape", help="Output filename")
    parser.add_argument("-f", "--frames", type=int, default=10, help="Number of frames")
    parser.add_argument("-p", "--payload", help="File containing arbitrary data to inject")
    parser.add_argument("-l", "--location", choices=["audio", "tag"], default="audio", help="Where to inject the payload data")
    
    args = parser.parse_args()
    
    payload_data = None
    if args.payload:
        try:
            with open(args.payload, 'rb') as f:
                payload_data = f.read()
        except Exception as e:
            print(f"Error reading payload file: {e}")
            sys.exit(1)
            
    build_ape_file(args.output, args.frames, payload_data, args.location)