package dev.httpcapture.capture_app

import android.app.Activity
import android.content.Intent
import android.content.ContentValues
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import android.net.VpnService
import android.os.Handler
import android.os.Looper
import android.net.ConnectivityManager
import android.provider.Settings
import android.security.KeyChain
import android.os.Build
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

class MainActivity : FlutterActivity() {
    private lateinit var channel: MethodChannel
    private var pending: MethodChannel.Result? = null
    private var exportPath: String? = null
    private var port = 8877
    private val certificateAuthority by lazy { CertificateAuthority(this) }
    private val handler = Handler(Looper.getMainLooper())
    private var starting: MethodChannel.Result? = null
    private fun networkState(): Map<String, Any> {
        val proxy = getSystemService(ConnectivityManager::class.java).defaultProxy
        val own = proxy != null && proxy.host in listOf("127.0.0.1", "localhost", "::1") && proxy.port == port
        val state = mapOf("active" to CaptureService.active(), "ownProxy" to own,
            "proxyHost" to (proxy?.host ?: ""), "proxyPort" to (proxy?.port ?: 0))
        if ((applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0) File(filesDir,"recovery-state.json").writeText(org.json.JSONObject(state).toString())
        return state
    }
    private fun stopAndReport(result: MethodChannel.Result, attempts: Int = 25) {
        CaptureService.shutdown()
        stopService(Intent(this, CaptureService::class.java))
        val state = networkState()
        if (state["ownProxy"] == true && attempts > 0) {
            handler.postDelayed({ stopAndReport(result,attempts-1) },200)
        } else if(state["ownProxy"] == true) {
            result.error("manual_proxy", "A manual Wi-Fi proxy remains. Restore it in Wi-Fi settings; Android does not permit this app to edit it.", null)
        } else result.success(state)
    }
    /** Only the public certificate is copied; the CA private key stays in Android Keystore. */
    private fun savePublicCa(): String {
        val info = certificateAuthority.info()
        val cert = File(info["path"] as String)
        val suffix = (info["fingerprint"] as String).replace(":", "").takeLast(8)
        val name = "HTTP-Capture-Root-$suffix.crt"
        val prefs = getSharedPreferences("capture_ca_export", MODE_PRIVATE)
        val previous = prefs.getString("uri", null)?.let { Uri.parse(it) }
        if(previous != null) {
            try { requireNotNull(contentResolver.openOutputStream(previous,"wt")).use { out -> cert.inputStream().use { it.copyTo(out) } }; return name }
            catch(_: Exception) { prefs.edit().remove("uri").apply() }
        }
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME,name)
            put(MediaStore.MediaColumns.MIME_TYPE,"application/x-x509-ca-cert")
            put(MediaStore.MediaColumns.RELATIVE_PATH,Environment.DIRECTORY_DOWNLOADS)
            put(MediaStore.MediaColumns.IS_PENDING,1)
        }
        val uri=requireNotNull(contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI,values))
        try {
            requireNotNull(contentResolver.openOutputStream(uri,"w")).use { out -> cert.inputStream().use { it.copyTo(out) } }
            contentResolver.update(uri,ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING,0) },null,null)
            prefs.edit().putString("uri",uri.toString()).apply()
        } catch(e: Exception) { contentResolver.delete(uri,null,null); throw e }
        return name
    }
    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)
        channel = MethodChannel(engine.dartExecutor.binaryMessenger, "dev.httpcapture/android")
        CaptureService.revoked = { runOnUiThread { channel.invokeMethod("revoked", null) } }
        networkState()
        channel.setMethodCallHandler { call, result ->
            try {
                when (call.method) {
                    "start" -> {
                        if (pending != null || starting != null) { result.error("busy", "Another system dialog is pending", null); return@setMethodCallHandler }
                        port = call.argument<Int>("port") ?: 8877
                        if (networkState()["ownProxy"] == true && !CaptureService.active()) {
                            result.error("manual_proxy", "Remove the old manual Wi-Fi proxy before starting. This build uses a temporary VPN proxy only.", null)
                            return@setMethodCallHandler
                        }
                        val intent = VpnService.prepare(this)
                        if (intent != null) { pending = result; startActivityForResult(intent, 701) }
                        else launchService(result)
                    }
                    "stop" -> stopAndReport(result)
                    "heartbeat" -> { networkState(); result.success(CaptureService.heartbeat()) }
                    "networkState" -> result.success(networkState())
                    "caInfo", "tlsIdentity" -> {
                        val host = call.argument<String>("host")
                        Thread {
                            try {
                                val ca = certificateAuthority
                                val value = if(call.method == "caInfo") ca.info() else ca.leaf(requireNotNull(host))
                                runOnUiThread { result.success(value) }
                            } catch(e: Exception) { runOnUiThread { result.error("certificate",e.message,null) } }
                        }.start()
                    }
                    "prepareCa" -> {
                        if(pending != null) { result.error("busy", "Another system dialog is pending", null); return@setMethodCallHandler }
                        Thread {
                            try {
                                val name=savePublicCa()
                                runOnUiThread {
                                    try {
                                        if(Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                                            startActivity(Intent(Settings.ACTION_SECURITY_SETTINGS))
                                            result.success("Downloads/$name 저장 완료. 보안 설정에서 CA 인증서 설치를 선택하세요.")
                                        } else {
                                            val path=certificateAuthority.info()["path"] as String
                                            val intent=KeyChain.createInstallIntent().putExtra(KeyChain.EXTRA_CERTIFICATE,File(path).readBytes()).putExtra(KeyChain.EXTRA_NAME,"HTTP Capture Local Root")
                                            pending=result
                                            try { startActivityForResult(intent,703) } catch(e: Exception) { pending=null; throw e }
                                        }
                                    } catch(e: Exception) { result.error("certificate",e.message,null) }
                                }
                            } catch(e: Exception) { runOnUiThread { result.error("certificate",e.message,null) } }
                        }.start()
                    }
                    "caInstall" -> {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                            startActivity(Intent(Settings.ACTION_SECURITY_SETTINGS)); result.success("settings")
                        } else {
                            if (pending != null) { result.error("busy", "Another system dialog is pending", null); return@setMethodCallHandler }
                            val path = certificateAuthority.info()["path"] as String
                            val intent = KeyChain.createInstallIntent().putExtra(KeyChain.EXTRA_CERTIFICATE,File(path).readBytes()).putExtra(KeyChain.EXTRA_NAME,"HTTP Capture Local Root")
                            pending = result
                            try { startActivityForResult(intent, 703) } catch(e: Exception) { pending = null; throw e }
                        }
                    }
                    "securitySettings" -> { startActivity(Intent(Settings.ACTION_SECURITY_SETTINGS)); result.success(null) }
                    "wifiSettings" -> { startActivity(Intent(Settings.ACTION_WIFI_SETTINGS)); result.success(null) }
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
    private fun launchService(result: MethodChannel.Result) {
        starting = result
        CaptureService.started = { error ->
            val reply = starting; starting = null
            if (error == null) reply?.success(networkState()) else reply?.error("vpn", error, null)
        }
        try { startForegroundService(Intent(this, CaptureService::class.java).putExtra("port",port)) }
        catch(e: Exception) { starting = null; CaptureService.started = null; result.error("vpn", e.message,null) }
        handler.postDelayed({
            if (starting === result) {
                starting = null; CaptureService.started = null; CaptureService.shutdown()
                result.error("vpn", "VPN startup timed out",null)
            }
        },15000)
    }
    @Deprecated("Activity result bridge")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 701) {
            val result = pending; pending = null
            if (resultCode == Activity.RESULT_OK) {
                try { if(result != null) launchService(result) }
                catch (e: Exception) { result?.error("vpn",e.message,null) }
            } else result?.error("vpn", "VPN permission denied", null)
        }
        if (requestCode == 703) {
            val result = pending; pending = null
            result?.success(if(resultCode == Activity.RESULT_OK) "installer_returned" else "cancelled")
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
        CaptureService.shutdown()
        CaptureService.started = null
        starting?.error("activity", "Activity destroyed",null); starting = null
        handler.removeCallbacksAndMessages(null)
        CaptureService.revoked = null
        stopService(Intent(this, CaptureService::class.java))
        pending?.error("activity", "Activity destroyed", null); pending = null
        super.onDestroy()
    }
}


