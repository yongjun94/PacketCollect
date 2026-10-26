package dev.httpcapture.capture_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.net.ProxyInfo
import android.net.VpnService
import android.os.ParcelFileDescriptor
import android.system.OsConstants

/** Proxy recommendation only: no routed packets or claim of full VPN capture. */
class CaptureService : VpnService() {
    companion object { var revoked: (() -> Unit)? = null }
    private var tunnel: ParcelFileDescriptor? = null
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("capture", "Local capture", NotificationManager.IMPORTANCE_LOW))
        val notification = Notification.Builder(this, "capture")
            .setContentTitle("HTTP Capture preview")
            .setContentText("Local HTTP proxy active · HTTPS is not decrypted")
            .setSmallIcon(android.R.drawable.stat_sys_upload).build()
        startForeground(31, notification)
        try {
            if (intent?.getBooleanExtra("vpn", false) == true) {
                tunnel?.close()
                tunnel = Builder().setSession("HTTP Capture proxy hint")
                    .addAddress("10.203.0.1", 32)
                    .allowFamily(OsConstants.AF_INET6)
                    .setHttpProxy(ProxyInfo.buildDirectProxy("127.0.0.1", intent.getIntExtra("port",8877)))
                    .setBlocking(false).establish()
                if (tunnel == null) throw IllegalStateException("VPN permission no longer available")
            }
        } catch (e: Exception) { revoked?.invoke(); stopSelf() }
        return START_NOT_STICKY
    }
    override fun onRevoke() { revoked?.invoke(); stopSelf() }
    override fun onTaskRemoved(rootIntent: Intent?) { stopSelf() }
    override fun onDestroy() { tunnel?.close(); tunnel = null; super.onDestroy() }
}
