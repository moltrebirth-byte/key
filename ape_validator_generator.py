#!/usr/bin/env python3
"""
ape_validator_generator.py
APE parser edge-case test suite generator.
Embeds a marker payload at every structural boundary and generates malformed variants.
"""

import struct
import os
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ---------------------------------------------------------------------------
# APE format constants (from Monkey's Audio SDK / public spec)
# ---------------------------------------------------------------------------

MAC_FORMAT_FLAG_HAS_PEAK_LEVEL          = (1 << 2)
MAC_FORMAT_FLAG_HAS_SEEK_ELEMENTS       = (1 << 4)
MAC_FORMAT_FLAG_CREATE_WAV_HEADER       = (1 << 5)

COMPRESSION_LEVEL_FAST        = 1000
COMPRESSION_LEVEL_NORMAL      = 2000
COMPRESSION_LEVEL_HIGH        = 3000
COMPRESSION_LEVEL_EXTRA_HIGH  = 4000
COMPRESSION_LEVEL_INSANE      = 5000

APE_DESCRIPTOR_BYTES  = 52
APE_HEADER_BYTES      = 24
APE_DESCRIPTOR_ID     = b'MAC '

MIN_VERSION = 3800   # oldest version with descriptor block
CURRENT_VERSION = 3990

PAYLOAD_MARKER = b'VALIDATION_TEST'

# ---------------------------------------------------------------------------
# Minimal valid WAV header (44 bytes, 1ch 44100Hz 16bit, 0 samples)
# ---------------------------------------------------------------------------

def make_wav_header(num_samples: int = 0, channels: int = 1,
                    sample_rate: int = 44100, bits: int = 16) -> bytes:
    byte_rate   = sample_rate * channels * (bits // 8)
    block_align = channels * (bits // 8)
    data_size   = num_samples * block_align
    riff_size   = 36 + data_size
    return struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF', riff_size, b'WAVE',
        b'fmt ', 16,
        1,            # PCM
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        b'data', data_size
    )

# ---------------------------------------------------------------------------
# APE structure builders
# ---------------------------------------------------------------------------

def build_descriptor(version: int,
                     descriptor_bytes: int,
                     header_bytes: int,
                     seektable_bytes: int,
                     wav_header_bytes: int,
                     audio_data_bytes: int,
                     wav_terminator_bytes: int,
                     md5: bytes = b'\x00' * 16) -> bytes:
    """
    APE_DESCRIPTOR (52 bytes):
      4   cID                'MAC '
      2   nVersion
      2   nPadding           0
      4   nDescriptorBytes
      4   nHeaderBytes
      4   nSeekTableBytes
      4   nWavHeaderBytes
      8   nAPEFrameDataBytes (lo + hi)
      4   nWavTerminatingBytes
      16  cFileMD5
    """
    assert len(md5) == 16
    return struct.pack('<4sHHIIII QII 16s',
        APE_DESCRIPTOR_ID,
        version,
        0,                    # padding
        descriptor_bytes,
        header_bytes,
        seektable_bytes,
        wav_header_bytes,
        audio_data_bytes,     # Q = uint64
        0,                    # high dword (unused in <3990 but keep 0)
        wav_terminator_bytes,
        md5
    )


def build_ape_header(compression_level: int = COMPRESSION_LEVEL_NORMAL,
                     format_flags: int = MAC_FORMAT_FLAG_CREATE_WAV_HEADER,
                     blocks_per_frame: int = 73728,
                     final_frame_blocks: int = 0,
                     total_frames: int = 0,
                     bits_per_sample: int = 16,
                     channels: int = 1,
                     sample_rate: int = 44100) -> bytes:
    """
    APE_HEADER (24 bytes):
      2   nCompressionLevel
      2   nFormatFlags
      4   nBlocksPerFrame
      4   nFinalFrameBlocks
      4   nTotalFrames
      2   nBitsPerSample
      2   nChannels
      4   nSampleRate
    """
    return struct.pack('<HHIIIHhI',
        compression_level,
        format_flags,
        blocks_per_frame,
        final_frame_blocks,
        total_frames,
        bits_per_sample,
        channels,
        sample_rate
    )


def build_seek_table(num_frames: int, base_offset: int = 0) -> bytes:
    """4 bytes per frame, each entry = absolute file offset of frame start."""
    entries = []
    for i in range(num_frames):
        entries.append(struct.pack('<I', base_offset + i * 8))
    return b''.join(entries)


def assemble_valid_ape(payload: bytes = b'',
                       payload_position: str = 'none',
                       version: int = CURRENT_VERSION) -> bytes:
    """
    Build a structurally valid (but audio-empty) APE file.
    payload_position controls where the marker is injected:
      'none'          - no injection
      'after_descriptor'
      'after_header'
      'after_seektable'
      'after_wavheader'
      'in_audiodata'
      'after_audiodata'
    """
    wav_hdr      = make_wav_header(0)
    seektable    = build_seek_table(0)
    audio_data   = b'\x00' * 8   # minimal non-empty audio region

    # Inject payload at requested position
    extra_descriptor = b''
    extra_header     = b''
    extra_seektable  = b''
    extra_wavhdr     = b''
    extra_audio      = b''
    extra_post       = b''

    if payload:
        if payload_position == 'after_descriptor':  extra_descriptor = payload
        elif payload_position == 'after_header':    extra_header     = payload
        elif payload_position == 'after_seektable': extra_seektable  = payload
        elif payload_position == 'after_wavheader': extra_wavhdr     = payload
        elif payload_position == 'in_audiodata':    extra_audio      = payload
        elif payload_position == 'after_audiodata': extra_post       = payload

    desc_bytes    = APE_DESCRIPTOR_BYTES + len(extra_descriptor)
    hdr_bytes     = APE_HEADER_BYTES     + len(extra_header)
    seek_bytes    = len(seektable)       + len(extra_seektable)
    wavhdr_bytes  = len(wav_hdr)         + len(extra_wavhdr)
    audio_bytes   = len(audio_data)      + len(extra_audio)

    descriptor = build_descriptor(
        version         = version,
        descriptor_bytes= desc_bytes,
        header_bytes    = hdr_bytes,
        seektable_bytes = seek_bytes,
        wav_header_bytes= wavhdr_bytes,
        audio_data_bytes= audio_bytes,
        wav_terminator_bytes = 0
    )

    ape_header = build_ape_header(
        format_flags = MAC_FORMAT_FLAG_CREATE_WAV_HEADER | MAC_FORMAT_FLAG_HAS_SEEK_ELEMENTS
    )

    return (
        descriptor      + extra_descriptor +
        ape_header      + extra_header     +
        seektable       + extra_seektable  +
        wav_hdr         + extra_wavhdr     +
        audio_data      + extra_audio      +
        extra_post
    )


# ---------------------------------------------------------------------------
# Edge-case generators
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    name:        str
    description: str
    data:        bytes
    expect_fail: bool = True   # True = parser should reject / handle gracefully


def gen_payload_positions(payload: bytes) -> List[TestCase]:
    cases = []
    positions = [
        ('after_descriptor', 'Payload injected between descriptor and APE header'),
        ('after_header',     'Payload injected between APE header and seek table'),
        ('after_seektable',  'Payload injected between seek table and WAV header'),
        ('after_wavheader',  'Payload injected between WAV header and audio data'),
        ('in_audiodata',     'Payload appended inside audio data region'),
        ('after_audiodata',  'Payload appended after all audio data (trailing garbage)'),
    ]
    for pos, desc in positions:
        data = assemble_valid_ape(payload=payload, payload_position=pos)
        cases.append(TestCase(
            name        = f'payload_{pos}',
            description = desc,
            data        = data,
            expect_fail = False   # structurally valid, payload is extra bytes
        ))
    return cases


def gen_version_edge_cases(payload: bytes) -> List[TestCase]:
    cases = []
    versions = [
        (0,      'Version 0 (below minimum)',           True),
        (1000,   'Version 1000 (pre-descriptor era)',   True),
        (3799,   'Version 3799 (just below min valid)', True),
        (3800,   'Version 3800 (minimum valid)',        False),
        (3990,   'Version 3990 (current)',              False),
        (4000,   'Version 4000 (above current)',        True),
        (0xFFFF, 'Version 0xFFFF (max uint16)',         True),
    ]
    for ver, desc, expect_fail in versions:
        data = assemble_valid_ape(payload=payload,
                                  payload_position='after_audiodata',
                                  version=ver)
        cases.append(TestCase(
            name        = f'version_{ver}',
            description = desc,
            data        = data,
            expect_fail = expect_fail
        ))
    return cases


def gen_descriptor_field_overflows(payload: bytes) -> List[TestCase]:
    """Corrupt individual descriptor size fields to overflow/underflow."""
    base = assemble_valid_ape(payload=payload, payload_position='in_audiodata')
    cases = []

    def patch_u32(data: bytes, offset: int, value: int) -> bytes:
        return data[:offset] + struct.pack('<I', value) + data[offset+4:]

    def patch_u64(data: bytes, offset: int, value: int) -> bytes:
        return data[:offset] + struct.pack('<Q', value) + data[offset+8:]

    cases.append(TestCase('descriptor_bytes_zero',
        'descriptor_bytes field set to 0',
        patch_u32(base, 8, 0), True))

    cases.append(TestCase('descriptor_bytes_max',
        'descriptor_bytes field set to 0xFFFFFFFF',
        patch_u32(base, 8, 0xFFFFFFFF), True))

    cases.append(TestCase('header_bytes_zero',
        'header_bytes field set to 0',
        patch_u32(base, 12, 0), True))

    cases.append(TestCase('header_bytes_max',
        'header_bytes field set to 0xFFFFFFFF',
        patch_u32(base, 12, 0xFFFFFFFF), True))

    cases.append(TestCase('seektable_bytes_max',
        'seektable_bytes field set to 0xFFFFFFFF (seek table overflow)',
        patch_u32(base, 16, 0xFFFFFFFF), True))

    cases.append(TestCase('wav_header_bytes_max',
        'wav_header_bytes field set to 0xFFFFFFFF',
        patch_u32(base, 20, 0xFFFFFFFF), True))

    cases.append(TestCase('audio_data_bytes_max',
        'audio_data_bytes (uint64) set to 0xFFFFFFFFFFFFFFFF',
        patch_u64(base, 24, 0xFFFFFFFFFFFFFFFF), True))

    cases.append(TestCase('wav_terminating_bytes_max',
        'wav_terminating_bytes set to 0xFFFFFFFF',
        patch_u32(base, 36, 0xFFFFFFFF), True))

    return cases


def gen_magic_corruptions(payload: bytes) -> List[TestCase]:
    base = assemble_valid_ape(payload=payload, payload_position='in_audiodata')
    cases = []

    cases.append(TestCase('wrong_magic',
        'ID field replaced with XXXX',
        b'XXXX' + base[4:], True))

    cases.append(TestCase('null_magic',
        'ID field set to 4 null bytes',
        b'\x00\x00\x00\x00' + base[4:], True))

    cases.append(TestCase('truncated_magic',
        'File is only 3 bytes (truncated before magic completes)',
        base[:3], True))

    cases.append(TestCase('empty_file',
        'Zero-byte file',
        b'', True))

    cases.append(TestCase('magic_only',
        'Only the 4-byte magic ID, no further data',
        APE_DESCRIPTOR_ID, True))

    return cases


def gen_truncation_cases(payload: bytes) -> List[TestCase]:
    base = assemble_valid_ape(payload=payload, payload_position='in_audiodata')
    cases = []
    total = len(base)
    boundaries = [
        (4,                    'truncated_after_magic'),
        (6,                    'truncated_after_version'),
        (APE_DESCRIPTOR_BYTES, 'truncated_after_descriptor'),
        (APE_DESCRIPTOR_BYTES + APE_HEADER_BYTES, 'truncated_after_ape_header'),
        (total // 2,           'truncated_at_midpoint'),
        (total - 1,            'truncated_last_byte'),
    ]
    for cut, name in boundaries:
        if cut < total:
            cases.append(TestCase(name,
                f'File truncated to {cut} bytes (of {total})',
                base[:cut], True))
    return cases


def gen_seek_table_edge_cases(payload: bytes) -> List[TestCase]:
    cases = []

    base = assemble_valid_ape()
    data = base[:16] + struct.pack('<I', 0xFFFFFF * 4) + base[20:]
    cases.append(TestCase('seektable_claim_huge',
        'Descriptor claims seek table of 0xFFFFFF * 4 bytes (allocation bomb)',
        data, True))

    wav_hdr   = make_wav_header(0)
    seektable = b''.join(struct.pack('<I', 0xDEADBEEF) for _ in range(16))
    audio     = payload + b'\x00' * 8
    desc = build_descriptor(
        version=CURRENT_VERSION,
        descriptor_bytes=APE_DESCRIPTOR_BYTES,
        header_bytes=APE_HEADER_BYTES,
        seektable_bytes=len(seektable),
        wav_header_bytes=len(wav_hdr),
        audio_data_bytes=len(audio),
        wav_terminator_bytes=0
    )
    hdr = build_ape_header(
        total_frames=16,
        format_flags=MAC_FORMAT_FLAG_CREATE_WAV_HEADER | MAC_FORMAT_FLAG_HAS_SEEK_ELEMENTS
    )
    data = desc + hdr + seektable + wav_hdr + audio
    cases.append(TestCase('seektable_past_eof',
        'Seek table entries all point to 0xDEADBEEF (past EOF)',
        data, True))

    seektable_rev = b''.join(
        struct.pack('<I', 0xFFFF - i * 4) for i in range(16)
    )
    desc2 = build_descriptor(
        version=CURRENT_VERSION,
        descriptor_bytes=APE_DESCRIPTOR_BYTES,
        header_bytes=APE_HEADER_BYTES,
        seektable_bytes=len(seektable_rev),
        wav_header_bytes=len(wav_hdr),
        audio_data_bytes=len(audio),
        wav_terminator_bytes=0
    )
    data2 = desc2 + hdr + seektable_rev + wav_hdr + audio
    cases.append(TestCase('seektable_reverse_order',
        'Seek table entries in descending order (spec violation)',
        data2, True))

    return cases


def gen_compression_level_cases(payload: bytes) -> List[TestCase]:
    cases = []
    levels = [
        (0,     'compression_zero',    True),
        (999,   'compression_999',     True),
        (1000,  'compression_fast',    False),
        (1500,  'compression_1500',    True),
        (5000,  'compression_insane',  False),
        (5001,  'compression_5001',    True),
        (0xFFFF,'compression_max',     True),
    ]
    for level, name, expect_fail in levels:
        wav_hdr = make_wav_header(0)
        audio   = payload + b'\x00' * 8
        desc = build_descriptor(
            version=CURRENT_VERSION,
            descriptor_bytes=APE_DESCRIPTOR_BYTES,
            header_bytes=APE_HEADER_BYTES,
            seektable_bytes=0,
            wav_header_bytes=len(wav_hdr),
            audio_data_bytes=len(audio),
            wav_terminator_bytes=0
        )
        hdr = build_ape_header(
            compression_level=level,
            format_flags=MAC_FORMAT_FLAG_CREATE_WAV_HEADER
        )
        data = desc + hdr + wav_hdr + audio
        cases.append(TestCase(name,
            f'Compression level = {level}',
            data, expect_fail))
    return cases


def gen_channel_sample_rate_cases(payload: bytes) -> List[TestCase]:
    cases = []
    variants = [
        (0,     44100, 16, 'channels_zero',           True),
        (1,     44100, 16, 'channels_mono',           False),
        (2,     44100, 16, 'channels_stereo',         False),
        (32,    44100, 16, 'channels_32',             True),
        (0xFFFF,44100, 16, 'channels_max',            True),
        (2,     0,     16, 'samplerate_zero',         True),
        (2,     8000,  16, 'samplerate_8k',           False),
        (2,     192000,16, 'samplerate_192k',         False),
        (2,     0xFFFFFFFF, 16, 'samplerate_max',     True),
        (2,     44100,  0, 'bits_zero',               True),
        (2,     44100,  8, 'bits_8',                  False),
        (2,     44100, 24, 'bits_24',                 False),
        (2,     44100, 32, 'bits_32',                 False),
        (2,     44100, 33, 'bits_33',                 True),
        (2,     44100, 0xFFFF, 'bits_max',            True),
    ]
    for ch, sr, bps, name, expect_fail in variants:
        wav_hdr = make_wav_header(0, max(ch, 1), max(sr, 1), max(bps, 8))
        audio   = payload + b'\x00' * 8
        desc = build_descriptor(
            version=CURRENT_VERSION,
            descriptor_bytes=APE_DESCRIPTOR_BYTES,
            header_bytes=APE_HEADER_BYTES,
            seektable_bytes=0,
            wav_header_bytes=len(wav_hdr),
            audio_data_bytes=len(audio),
            wav_terminator_bytes=0
        )
        hdr = build_ape_header(
            channels=ch,
            sample_rate=sr,
            bits_per_sample=bps,
            format_flags=MAC_FORMAT_FLAG_CREATE_WAV_HEADER
        )
        data = desc + hdr + wav_hdr + audio
        cases.append(TestCase(name,
            f'channels={ch} sample_rate={sr} bits={bps}',
            data, expect_fail))
    return cases


def gen_md5_cases(payload: bytes) -> List[TestCase]:
    base = assemble_valid_ape(payload=payload, payload_position='in_audiodata')
    cases = []
    md5_offset = 36

    cases.append(TestCase('md5_all_ff',
        'MD5 field set to 0xFF * 16 (invalid checksum)',
        base[:md5_offset] + b'\xFF' * 16 + base[md5_offset+16:], True))

    cases.append(TestCase('md5_all_zero',
        'MD5 field set to 0x00 * 16 (null checksum)',
        base[:md5_offset] + b'\x00' * 16 + base[md5_offset+16:], True))

    return cases


def gen_overlapping_regions(payload: bytes) -> List[TestCase]:
    cases = []
    wav_hdr = make_wav_header(0)
    audio   = payload + b'\x00' * 8

    desc = build_descriptor(
        version=CURRENT_VERSION,
        descriptor_bytes=APE_DESCRIPTOR_BYTES,
        header_bytes=APE_HEADER_BYTES,
        seektable_bytes=0xFFFFFFF0,
        wav_header_bytes=0x20,
        audio_data_bytes=len(audio),
        wav_terminator_bytes=0
    )
    hdr = build_ape_header(format_flags=MAC_FORMAT_FLAG_CREATE_WAV_HEADER)
    cases.append(TestCase('region_sum_overflow',
        'seektable_bytes + wav_header_bytes overflows uint32',
        desc + hdr + wav_hdr + audio, True))

    desc2 = build_descriptor(
        version=CURRENT_VERSION,
        descriptor_bytes=10,
        header_bytes=APE_HEADER_BYTES,
        seektable_bytes=0,
        wav_header_bytes=len(wav_hdr),
        audio_data_bytes=len(audio),
        wav_terminator_bytes=0
    )
    cases.append(TestCase('descriptor_bytes_too_small',
        'descriptor_bytes=10, points inside the descriptor itself',
        desc2 + hdr + wav_hdr + audio, True))

    return cases


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(cases: List[TestCase], output_dir: Path) -> dict:
    report = {
        'total_cases':    len(cases),
        'expect_fail':    sum(1 for c in cases if c.expect_fail),
        'expect_pass':    sum(1 for c in cases if not c.expect_fail),
        'output_dir':     str(output_dir),
        'payload_marker': PAYLOAD_MARKER.decode(),
        'cases': []
    }
    for c in cases:
        report['cases'].append({
            'name':        c.name,
            'description': c.description,
            'file':        f'{c.name}.ape',
            'size_bytes':  len(c.data),
            'expect_fail': c.expect_fail,
            'has_payload': PAYLOAD_MARKER in c.data,
            'payload_offsets': [
                i for i in range(len(c.data))
                if c.data[i:i+len(PAYLOAD_MARKER)] == PAYLOAD_MARKER
            ]
        })
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='APE parser edge-case test suite generator'
    )
    parser.add_argument('--payload-file', '-p',
        default=None,
        help='File whose content is used as the embedded payload. '
             'Defaults to the string VALIDATION_TEST.')
    parser.add_argument('--output-dir', '-o',
        default='ape_test_suite',
        help='Directory to write test files and report into.')
    parser.add_argument('--report-only', action='store_true',
        help='Print report to stdout without writing files.')
    args = parser.parse_args()

    if args.payload_file:
        payload = Path(args.payload_file).read_bytes()
    else:
        payload = PAYLOAD_MARKER

    print(f'[*] Payload: {len(payload)} bytes')
    print(f'[*] Marker present in payload: {PAYLOAD_MARKER in payload}')

    all_cases: List[TestCase] = []
    all_cases += gen_payload_positions(payload)
    all_cases += gen_version_edge_cases(payload)
    all_cases += gen_descriptor_field_overflows(payload)
    all_cases += gen_magic_corruptions(payload)
    all_cases += gen_truncation_cases(payload)
    all_cases += gen_seek_table_edge_cases(payload)
    all_cases += gen_compression_level_cases(payload)
    all_cases += gen_channel_sample_rate_cases(payload)
    all_cases += gen_md5_cases(payload)
    all_cases += gen_overlapping_regions(payload)

    print(f'[*] Total test cases: {len(all_cases)}')

    output_dir = Path(args.output_dir)

    if not args.report_only:
        output_dir.mkdir(parents=True, exist_ok=True)
        for case in all_cases:
            out_path = output_dir / f'{case.name}.ape'
            out_path.write_bytes(case.data)
        print(f'[+] Written {len(all_cases)} files to {output_dir}/')

    report = generate_report(all_cases, output_dir)
    report_path = output_dir / 'report.json'

    if not args.report_only:
        report_path.write_text(json.dumps(report, indent=2))
        print(f'[+] Report: {report_path}')
    else:
        print(json.dumps(report, indent=2))

    print()
    print(f'{"Case":<45} {"Size":>8}  {"Expect fail":<12}  {"Payload offsets"}')
    print('-' * 90)
    for c in report['cases']:
        offsets = c['payload_offsets'][:3]
        off_str = str(offsets) + ('...' if len(c['payload_offsets']) > 3 else '')
        print(f'{c["name"]:<45} {c["size_bytes"]:>8}  '
              f'{str(c["expect_fail"]):<12}  {off_str}')


if __name__ == '__main__':
    main()
