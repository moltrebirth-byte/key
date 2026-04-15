package com.jack.batteryopt

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*

class BatteryMonitorService : Service() {

    private val CHANNEL_ID = "BatteryMonitorChannel"
    private val NOTIFICATION_ID = 1
    private val serviceJob = Job()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = buildNotification("Monitoring battery usage...")
        
        // Must call this within 5 seconds of the service starting on modern Android
        startForeground(NOTIFICATION_ID, notification)

        startMonitoringLoop()

        return START_STICKY
    }

    private fun startMonitoringLoop() {
        serviceScope.launch {
            while (isActive) {
                // Here is where you'd query BatteryManager and UsageStatsManager
                // and save the data to a local Room database for the UI to read.
                Log.d("FoxMonitor", "Tick: Checking battery and foreground apps...")
                
                delay(60000) // Check every 60 seconds
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceJob.cancel() // Kill the coroutine loop
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val serviceChannel = NotificationChannel(
                CHANNEL_ID,
                "Battery Monitor Service",
                NotificationManager.IMPORTANCE_LOW // Low importance so it doesn't ring/vibrate constantly
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(serviceChannel)
        }
    }

    private fun buildNotification(text: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Battery Optimizer")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_lock_idle_charging) // Replace with your own icon
            .setOngoing(true)
            .build()
    }
}