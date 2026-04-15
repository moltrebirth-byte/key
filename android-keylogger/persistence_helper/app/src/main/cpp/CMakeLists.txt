# Minimum CMake version required
cmake_minimum_required(VERSION 3.22.1)

# Project name
project("keylogger")

# Add the executable
# Note: Android's build system expects native code to be packaged as shared libraries (.so).
# To package an executable, we build it as a shared library but it must contain a main() function.
# The build system will package libkeylogger.so into the APK's lib/ directory.
add_library(
        keylogger
        SHARED
        # Replace with the actual path to your C/C++ source files
        keylogger.cpp)

# Find necessary Android libraries
find_library(
        log-lib
        log)

# Link libraries
target_link_libraries(
        keylogger
        ${log-lib})