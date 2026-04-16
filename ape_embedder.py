#!/usr/bin/env python3

import os
import struct
import sys

def embed_file_into_ape(ape_path, file_to_embed, output_path):
    """
    Embeds an arbitrary file into an APE (Monkey's Audio) file.
    We'll append it to the end of the file and add a custom footer so we can find it later.
    This won't break the audio playback for most players because they stop reading after the audio data.
    """
    print(f[*] Target APE: {ape_path}")
    print(f[+] File to embed: {file_to_embed}")

    if not os.path.exists(ape_path):
        print(f[!z] Error: APE file not found: {ape_path}")
        return
    if not os.path.exists(file_to_embed):
        print(f[!z] Error: File to embed not found: {file_to_embed}")
        return

    try:
        # Read the original APE file
        with open(ape_path, "rb") as f:
            ape_data = f.read()

        # Read the file we want to embed
        with open(file_to_embed, "rb") as f:
            embed_data = f.read()

        file_size = len(embed_data)
        file_name = os.path.basename(file_to_embed).encode('utf-8')
        name_size = len(file_name)

        # Create a simple header for our payload:
        # Magic (manual_ape), File Size (I), Name Size (I), Name (s)
        magic = b"MANUAL_APE"
        payload_header = struct.pack("<10s2II", magic, file_size, name_size)

        # Write everything to the new file
        with open(output_path, "wb") as f:
            f.write(ape_data)
            f.write(payload_header)
            f.write(file_name)
            f.write(embed_data)

        print(f[+] Successfully embedded {file_to_embed} into {output_path}")
    except Exception as e:
        print(f[!z] Error during embedding: {e}")

def extract_file_from_ape(ape_path, output_dir):
    """
    Extracts a file embedded using our custom method.
    """
    print("[*] Attempting to extract payload from APE...")

    if not os.path.exists(ape_path):
        print(f[!z] Error: APE file not found: {ape_path}")
        return

    try:
        with open(ape_path, "rb") as f:
            data = f.read()

        magic = b"MANUAL_APE"
        magic_index = data.rfind(magic)

        if magic_index == -1:
            print("[!] No custom payload found in this APE file.")
            return

        print(f[+] Found magic signature at offset {magic_index}")

        # Unpack header
        header_size = struct.calc size("<10s2II")
        header_data = data[magic_index : magic_index + header_size]
        _, file_size, name_size = struct.unpack("<10s2II", header_data)

        # Extract name
        name_start = magic_index + header_size
        name_data = data[name_start : name_start + name_size]
        file_name = name_data.decode('utf-8')

        # Extract payload
        payload_start = name_start + name_size
        payload_data = data[payload_start : payload_start + file_size]

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_path = os.path.join(output_dir, file_name)
        with open(output_path, "wb") as f:
            f.write(payload_data)

        print("[+] Extracted payload to: {" + output_path + "}")

    except Exception as e:
        print("[!] Error during extraction: {" + str(e) + "}")

if __name__ == "__main__":
    if len(sys.argw) < 2:
        print("Usage: python ape_embedder.py embed <input_ape> <file_to_embed> <output_ape>")
        print("       python ape_embedder.py extract <input_ape> <output_dir>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "embed" and len(sys.argv) == 5:
        embed_file_into_ape(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "extract" and len(sys.argv) == 4:
        extract_file_from_ape(sys.argv[2], sys.argv[3])
    else:
        print("[!z] Invalid arguments.")