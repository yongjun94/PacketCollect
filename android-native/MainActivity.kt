package dev.httpcapture.capture_app

import android.app.Activity
import android.content.Intent
import android.net.VpnService
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

class MainActivity : FlutterActivity() {
    private lateinit var channel: MethodChannel
    private var pending: MethodChannel.Result? = null
    private var exportPath: String? = null
    private var port = 8877
    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)
        channel = MethodChannel(engine.dartExecutor.binaryMessenger, "dev.httpcapture/android")
        CaptureService.revoked = { runOnUiThread { channel.invokeMethod("revoked", null) } }
        channel.setMethodCallHandler { call, result ->
            try {
                when (call.method) {
                    "start" -> {
                        if (pending != null) { result.error("busy", "Another system dialog is pending", null); return@setMethodCallHandler }
                        port = call.argument<Int>("port") ?: 8877
                        val vpn = call.argument<Boolean>("vpn") == true
                        val intent = if (vpn) VpnService.prepare(this) else null
                        if (intent != null) { pending = result; startActivityForResult(intent, 701) }
                        else { launchService(vpn); result.success(null) }
                    }
                    "stop" -> { stopService(Intent(this, CaptureService::class.java)); result.success(null) }
                    "export" -> {
                        if (pending != null) { result.error("busy", "Another system dialog is pending", null); return@setMethodCallHandler }
                        val file = File(call.argument<String>("path")!!).canonicalFile
                        // Only files from this app's private data can be exported.
                        if (!file.path.startsWith(File(applicationInfo.dataDir).canonicalPath + "/")) throw SecurityException("Export outside app storage")
                        exportPath = file.path; pending = result
                        startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                            addCategory(Intent.CATEGORY_OPENABLE)
                            type = "application/octet-stream"
                            putExtra(Intent.EXTRA_TITLE, call.argument<String>("name"))
                        }, 702)
                    }
                    else -> result.notImplemented()
                }
            } catch (e: Exception) { result.error("android", e.message, null) }
        }
    }
    private fun launchService(vpn: Boolean) {
        startForegroundService(Intent(this, CaptureService::class.java).putExtra("vpn", vpn).putExtra("port", port))
    }
    @Deprecated("Activity result bridge")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 701) {
            val result = pending; pending = null
            if (resultCode == Activity.RESULT_OK) {
                try { launchService(true); result?.success(null) }
                catch (e: Exception) { result?.error("vpn",e.message,null) }
            } else result?.error("vpn", "VPN permission denied", null)
        }
        if (requestCode == 702) {
            val result = pending; val path = exportPath; pending = null; exportPath = null
            val uri = data?.data
            if (resultCode != Activity.RESULT_OK || uri == null || path == null) { result?.success(false); return }
            Thread {
                try {
                    contentResolver.openOutputStream(uri, "wt").use { out ->
                        requireNotNull(out); File(path).inputStream().use { it.copyTo(out) }
                    }
                    runOnUiThread { result?.success(true) }
                } catch (e: Exception) { runOnUiThread { result?.error("export",e.message,null) } }
            }.start()
        }
    }
    override fun onDestroy() {
        CaptureService.revoked = null
        stopService(Intent(this, CaptureService::class.java))
        pending?.error("activity", "Activity destroyed", null); pending = null
        super.onDestroy()
    }
}
