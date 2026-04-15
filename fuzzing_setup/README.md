# Audio Codec Fuzzing Setup

This directory contains a basic setup for fuzzing audio parsing logic using **libFuzzer** and **AddressSanitizer (ASan)**.

## Files
*   `fuzz_harness.cpp`: The entry point for libFuzzer (`LLVMFuzzerTestOneInput`). It takes mutated byte arrays and feeds them into the target function.
*   `setup_fuzzer.sh`: A bash script to install Clang, create a starting corpus, and compile the harness with the necessary sanitizer flags.

## How to Use

1.  **Run the setup script:**
    ```bash
    chmod +x setup_fuzzer.sh
    ./setup_fuzzer.sh
    ```

2.  **Run the fuzzer:**
    ```bash
    ./audio_fuzzer corpus/
    ```

## Interpreting Results

libFuzzer will run continuously, mutating the inputs in the `corpus/` directory. 

*   **Coverage:** It tracks code coverage. If a mutation hits new code paths, it saves that mutation back to the corpus to use as a base for future mutations.
*   **Crashes:** If the target function crashes (e.g., a segfault, buffer overflow, or use-after-free), ASan will catch it, halt the fuzzer, and print a detailed stack trace.
*   **Artifacts:** The input file that caused the crash will be saved to the disk (e.g., `crash-1234567890abcdef`). You can pass this file directly back to the compiled binary to reproduce the crash in a debugger like `gdb` or `lldb`.

## Applying to Android (AOSP)

To fuzz actual Android codecs (like `libstagefright`), you don't compile it standalone like this. You use Android's build system (`Soong`).

1.  Write a similar `LLVMFuzzerTestOneInput` harness in the AOSP tree.
2.  Create an `cc_fuzz` module in the `Android.bp` file.
3.  Build it using `m my_audio_fuzzer`.
4.  Push it to a rooted device or emulator and run it via ADB.