package dev.httpcapture.capture_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.net.ProxyInfo
import android.net.VpnService
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import android.system.OsConstants

/** The proxy belongs to this VPN network only. No persistent Wi-Fi settings. */
class CaptureService : VpnService() {
    companion object {
        var revoked: (() -> Unit)? = null
        var started: ((String?) -> Unit)? = null
        private var instance: CaptureService? = null
        fun active(): Boolean = instance?.tunnel != null
        fun heartbeat(): Boolean { instance?.lastBeat = SystemClock.elapsedRealtime(); return active() }
        fun shutdown(notify: Boolean = false) { instance?.release(notify) }
    }
    private var tunnel: ParcelFileDescriptor? = null
    private var lastBeat = SystemClock.elapsedRealtime()
    private val handler = Handler(Looper.getMainLooper())
    private val watchdog = object : Runnable {
        override fun run() {
            if (SystemClock.elapsedRealtime() - lastBeat > 10000) { release(true); return }
            handler.postDelayed(this, 2000)
        }
    }
    override fun onCreate() { super.onCreate(); instance = this }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val callback = started; started = null
        try {
            require(intent != null) { "Capture must be started explicitly" }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(NotificationChannel("capture", "Local capture", NotificationManager.IMPORTANCE_LOW))
            startForeground(31, Notification.Builder(this, "capture")
                .setContentTitle("HTTP Capture Safe Preview")
                .setContentText("VPN proxy · released when capture or app stops")
                .setSmallIcon(android.R.drawable.stat_sys_upload).build())
            tunnel?.close()
            tunnel = Builder().setSession("HTTP Capture temporary proxy")
                .addAddress("10.203.0.1", 32)
                .allowFamily(OsConstants.AF_INET6)
                .setHttpProxy(ProxyInfo.buildDirectProxy("127.0.0.1", intent.getIntExtra("port",8877)))
                .setBlocking(false).establish()
            check(tunnel != null) { "VPN permission no longer available" }
            lastBeat = SystemClock.elapsedRealtime()
            handler.removeCallbacks(watchdog); handler.postDelayed(watchdog,2000)
            callback?.invoke(null)
        } catch (e: Exception) { release(false); callback?.invoke(e.message ?: "VPN startup failed") }
        return START_NOT_STICKY
    }
    private fun release(notify: Boolean) {
        handler.removeCallbacks(watchdog)
        val wasActive = tunnel != null
        try { tunnel?.close() } finally { tunnel = null; stopForeground(STOP_FOREGROUND_REMOVE); stopSelf() }
        if (notify && wasActive) revoked?.invoke()
    }
    override fun onRevoke() { release(true) }
    override fun onTaskRemoved(rootIntent: Intent?) { release(true) }
    override fun onDestroy() {
        handler.removeCallbacks(watchdog)
        tunnel?.close(); tunnel = null
        if (instance === this) instance = null
        super.onDestroy()
    }
}
