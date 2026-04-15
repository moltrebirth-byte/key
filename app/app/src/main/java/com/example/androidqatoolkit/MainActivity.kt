package com.example.androidqatoolkit

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var deviceInfoText: TextView
    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        deviceInfoText = findViewById(R.id.deviceInfoText)
        statusText = findViewById(R.id.statusText)

        val refreshButton = findViewById<Button>(R.id.refreshInfoButton)
        val exportLogsButton = findViewById<Button>(R.id.exportLogsButton)
        val openDevSettingsButton = findViewById<Button>(R.id.openDevSettingsButton)

        refreshButton.setOnClickListener {
            renderDeviceInfo()
        }

        exportLogsButton.setOnClickListener {
            exportAppLogPlaceholder()
        }

        openDevSettingsButton.setOnClickListener {
            startActivity(Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS))
        }

        renderDeviceInfo()
    }

    private fun renderDeviceInfo() {
        val info = buildString {
            appendLine("Manufacturer: ${Build.MANUFACTURER}")
            appendLine("Model: ${Build.MODEL}")
            appendLine("Device: ${Build.DEVICE}")
            appendLine("Android Version: ${Build.VERSION.RELEASE}")
            appendLine("SDK: ${Build.VERSION.SDK_INT}")
        }
        deviceInfoText.text = info
        statusText.text = getString(R.string.status_ready)
    }

    private fun exportAppLogPlaceholder() {
        val dir = File(filesDir, "exports")
        if (!dir.exists()) {
            dir.mkdirs()
        }

        val stamp = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(Date())
        val outFile = File(dir, "session-$stamp.txt")
        val content = buildString {
            appendLine("Android QA Toolkit Export")
            appendLine("Timestamp: $stamp")
            appendLine("Manufacturer: ${Build.MANUFACTURER}")
            appendLine("Model: ${Build.MODEL}")
            appendLine("Android: ${Build.VERSION.RELEASE}")
            appendLine("SDK: ${Build.VERSION.SDK_INT}")
        }

        outFile.writeText(content)
        statusText.text = "Exported: ${outFile.absolutePath}"
        Toast.makeText(this, "Export saved", Toast.LENGTH_SHORT).show()
    }
}
