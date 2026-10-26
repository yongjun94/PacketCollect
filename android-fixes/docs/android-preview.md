# Android Safe Preview: temporary VPN proxy

This version removes manual Wi-Fi proxy mode. Standard Android apps cannot restore arbitrary user-managed Wi-Fi proxy settings. Leave Wi-Fi proxy at its original setting; the app creates a temporary VPN-scoped proxy instead. A stale loopback manual proxy is detected before capture starts and requires one-time removal in Android settings.

Stop closes the VPN before the local proxy listener. Back exit, Activity destruction, task removal, system VPN revocation, a missing Flutter heartbeat (10 seconds), and process termination release the VPN. No persistent Wi-Fi settings are written. Always-on VPN is disabled for this preview; do not enable VPN lockdown. Proxy-aware clients only, no full packet tunnel or HTTPS decryption.

The safe preview has applicationId dev.httpcapture.capture_app.safe, separate from the first preview, to preserve existing captured data and avoid replacing a debug-signed APK with a different ephemeral CI signing key. It can be installed alongside the old preview. Do not run both captures simultaneously.

Lifecycle recovery tests are included in android-scripts/android_device_smoke.py. They assert Android's actual ConnectivityManager.defaultProxy points at the local VPN proxy during capture and no longer does after Stop/Back exit/force-stop plus restart, and remains active for12seconds after Home. Real device behavior must still be checked.

Android10+; debug signed; no production license/security audit. Session model and exporters unchanged. Switching apps keeps capture active while the Flutter engine remains alive. The native heartbeat watchdog releases VPN if that engine stops responding. HTTP headers are parsed/normalized; body files capped at64MiB each with explicit partial status. Export via user-selected Android document provider; choose local storage to avoid cloud providers. SAZ/HAR importer compatibility for this variant needs acceptance testing.
