package com.jack.sysinfo

import android.content.Context
import android.os.BatteryManager
import android.os.Bundle
import android.os.SystemClock
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    SysInfoScreen(this)
                }
            }
        }
    }
}

@Composable
fun SysInfoScreen(context: Context) {
    // State variables to trigger recomposition on refresh
    var batteryLevel by remember { mutableIntStateOf(getBatteryLevel(context)) }
    var uptime by remember { mutableStateOf(getUptime()) }

    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = "System Info", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(32.dp))
        
        Text(text = "Battery: ${batteryLevel}%", style = MaterialTheme.typography.bodyLarge)
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(text = "Uptime: $uptime", style = MaterialTheme.typography.bodyLarge)
        Spacer(modifier = Modifier.height(32.dp))
        
        Button(onClick = {
            batteryLevel = getBatteryLevel(context)
            uptime = getUptime()
        }) {
            Text("Refresh")
        }
    }
}

fun getBatteryLevel(context: Context): Int {
    val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
    // Pulling the capacity property directly. No broadcast receiver needed for a simple one-shot read.
    return batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
}

fun getUptime(): String {
    // elapsedRealtime includes time spent in sleep, which is usually what you want for uptime
    val uptimeMillis = SystemClock.elapsedRealtime()
    val hours = TimeUnit.MILLISECONDS.toHours(uptimeMillis)
    val minutes = TimeUnit.MILLISECONDS.toMinutes(uptimeMillis) % 60
    val seconds = TimeUnit.MILLISECONDS.toSeconds(uptimeMillis) % 60
    return String.format("%02d:%02d:%02d", hours, minutes, seconds)
}