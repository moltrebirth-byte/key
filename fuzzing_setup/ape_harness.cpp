#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <iostream>

// =========================================================================
// Generic APE (Monkey's Audio) Parser Harness
// This harness demonstrates parsing the structural elements of an APE file.
// It does NOT implement actual audio decoding or target specific CVEs.
// =========================================================================

// APE Descriptor (present in MAC >= 3.980)
struct APEDescriptor {
    char magic[4];      // "MAC "
    uint16_t version;   // e.g., 3990
    uint16_t padding;
    uint32_t descriptorBytes;
    uint32_t headerBytes;
    uint32_t seekTableBytes;
    uint32_t wavHeaderBytes;
    uint32_t audiodataBytes;
    uint32_t audiodataBytesHigh;
    uint32_t wavTailBytes;
    uint8_t md5[16];
};

// APE Header
struct APEHeader {
    uint16_t compressionLevel;
    uint16_t formatFlags;
    uint32_t blocksPerFrame;
    uint32_t finalFrameBlocks;
    uint32_t totalFrames;
    uint16_t bps;
    uint16_t channels;
    uint32_t sampleRate;
};

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Need at least the size of the descriptor to start parsing
    if (size < sizeof(APEDescriptor)) {
        return 0;
    }

    const uint8_t* ptr = data;
    size_t remaining = size;

    // 1. Parse Descriptor
    APEDescriptor descriptor;
    memcpy(&descriptor, ptr, sizeof(APEDescriptor));
    
    // Check magic bytes ("MAC ")
    if (descriptor.magic[0] != 'M' || descriptor.magic[1] != 'A' || 
        descriptor.magic[2] != 'C' || descriptor.magic[3] != ' ') {
        return 0; // Not an APE file
    }

    // Basic bounds checking based on descriptor values
    // A real decoder would validate these extensively to prevent OOB reads/writes
    if (descriptor.descriptorBytes > remaining || 
        descriptor.headerBytes > remaining ||
        (descriptor.descriptorBytes + descriptor.headerBytes) > remaining) {
        return 0;
    }

    ptr += descriptor.descriptorBytes;
    remaining -= descriptor.descriptorBytes;

    // 2. Parse Header
    if (remaining < sizeof(APEHeader)) {
        return 0;
    }

    APEHeader header;
    memcpy(&header, ptr, sizeof(APEHeader));

    // A real decoder would now use header.blocksPerFrame, header.totalFrames, etc.
    // to allocate memory and begin parsing the Seek Table and Audio Data frames.
    // Fuzzers often find bugs when these calculated sizes integer-overflow or 
    // mismatch the actual remaining buffer size.

    // Example of logic a fuzzer might stress:
    // uint64_t totalSamples = (uint64_t)header.totalFrames * header.blocksPerFrame;
    // if (totalSamples > MAX_ALLOWED) { ... }

    return 0;
}