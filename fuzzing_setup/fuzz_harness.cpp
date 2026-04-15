#include <stdint.h>
#include <stddef.h>
#include <iostream>

// =========================================================================
// Mock Audio Decoder
// In a real AOSP environment, this would call into libstagefright, 
// MediaCodec, or a specific extractor (e.g., MP3Extractor, WAVExtractor).
// =========================================================================
extern "C" int decode_audio_frame(const uint8_t *data, size_t size) {
    // Need at least a basic header size to process
    if (size < 4) return 0;

    // Fake vulnerability for demonstration purposes.
    // If the fuzzer mutates the input to start with "FOX!", it triggers a null pointer dereference.
    // AddressSanitizer (ASan) will catch this and generate a crash report.
    if (data[0] == 'F' && data[1] == 'O' && data[2] == 'X' && data[3] == '!') {
        volatile int *crash = nullptr;
        *crash = 1; // BOOM
    }

    // Simulate parsing logic
    uint32_t header = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3];
    if (header == 0xFFFB) {
        // MP3 sync word found, do something...
    }

    return 0;
}

// =========================================================================
// libFuzzer Entry Point
// The fuzzer engine repeatedly calls this function with mutated byte arrays.
// =========================================================================
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Pass the mutated data directly to the target function
    decode_audio_frame(data, size);
    
    // Always return 0. Non-zero return values are reserved for future fuzzer features.
    return 0;
}