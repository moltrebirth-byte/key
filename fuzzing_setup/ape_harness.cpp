#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <iostream>

// =========================================================================
// Generic APE (Monkey's Audio) Parser Harness - Extended
// This harness demonstrates parsing the structural elements of an APE file,
// including the Seek Table and APEv2 tags.
// =========================================================================

struct APEDescriptor {
    char magic[4];      // "MAC "
    uint16_t version;
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

// APEv2 Tag Header/Footer (32 bytes)
struct APETagFooter {
    char preamble[8]; // "APETAGEX"
    uint32_t version; // 2000
    uint32_t size;    // Tag size including footer, excluding header
    uint32_t itemCount;
    uint32_t flags;
    char reserved[8];
};

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < sizeof(APEDescriptor)) {
        return 0;
    }

    const uint8_t* ptr = data;
    size_t remaining = size;

    // 1. Parse Descriptor
    APEDescriptor descriptor;
    memcpy(&descriptor, ptr, sizeof(APEDescriptor));
    
    if (descriptor.magic[0] != 'M' || descriptor.magic[1] != 'A' || 
        descriptor.magic[2] != 'C' || descriptor.magic[3] != ' ') {
        return 0;
    }

    // Comprehensive bounds checking for the descriptor fields
    // Prevent integer overflow when summing sizes
    uint64_t totalHeaderSize = (uint64_t)descriptor.descriptorBytes + 
                               descriptor.headerBytes + 
                               descriptor.seekTableBytes + 
                               descriptor.wavHeaderBytes;

    if (descriptor.descriptorBytes < sizeof(APEDescriptor) || 
        totalHeaderSize > remaining) {
        return 0;
    }

    ptr += descriptor.descriptorBytes;
    remaining -= descriptor.descriptorBytes;

    // 2. Parse Header
    if (descriptor.headerBytes < sizeof(APEHeader) || remaining < descriptor.headerBytes) {
        return 0;
    }

    APEHeader header;
    memcpy(&header, ptr, sizeof(APEHeader));
    
    ptr += descriptor.headerBytes;
    remaining -= descriptor.headerBytes;

    // 3. Parse Seek Table
    // The seek table is an array of 32-bit unsigned integers
    if (descriptor.seekTableBytes > 0) {
        if (remaining < descriptor.seekTableBytes) {
            return 0;
        }
        
        // A real decoder would allocate memory here based on totalFrames
        // Fuzzers often find issues if seekTableBytes doesn't match totalFrames * 4
        uint32_t expectedSeekTableSize = header.totalFrames * sizeof(uint32_t);
        
        // We just advance the pointer to simulate parsing it
        ptr += descriptor.seekTableBytes;
        remaining -= descriptor.seekTableBytes;
    }

    // 4. Parse APEv2 Tags (usually at the end of the file)
    // We check if the last 32 bytes match the APETAGEX footer
    if (size >= sizeof(APETagFooter)) {
        const uint8_t* footerPtr = data + size - sizeof(APETagFooter);
        APETagFooter tagFooter;
        memcpy(&tagFooter, footerPtr, sizeof(APETagFooter));

        if (memcmp(tagFooter.preamble, "APETAGEX", 8) == 0) {
            // Tag found. Validate its size against the total file size
            if (tagFooter.size > size || tagFooter.size < sizeof(APETagFooter)) {
                return 0; // Invalid tag size
            }
            
            // A real parser would now jump back 'tagFooter.size' bytes 
            // and begin parsing the individual tag items (key/value pairs).
            // Fuzzers find bugs in how those items are delimited and allocated.
        }
    }

    return 0;
}