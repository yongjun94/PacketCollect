# Android preview scope

Android 10/API29 or newer. Debug-key signed test APK, not production-signed or submitted to Play. Windows implementation is unchanged.

## Implemented
- Device-local Dart HTTP proxy bound to IPv4 loopback:8877, no Python dependency and no remote listener.
- HTTP request/response streaming, duplicate parsed headers, binary body files, common SQLite session model, capture pause/start/stop, basic filter (last 200 matching sessions displayed).
- Each captured body is capped at 64 MiB; truncation is explicit and forwarding continues. Header casing/order is normalized by Dart, upstream HTTP version is not available and is explicitly labeled as normalized. No raw packet fidelity claim.
- SAZ/HAR reuse existing exporters. Android Storage Access Framework creates a user-selected document; providers can include cloud accounts, so choose local storage. App itself does not upload captured traffic.
- Native foreground service; optional user-approved VpnService advertises a local HTTP proxy. This is a recommendation for proxy-aware clients, NOT a packet tunnel. No routes or packet processing engine are installed. VPN/proxy behavior on devices remains unverified. Other VPNs cannot be used concurrently.
- HTTPS CONNECT tunnels forward encrypted bytes without recording decrypted traffic; tunnel session metadata appears when the connection closes. No CA generation, certificate installation, TLS decryption or pinning bypass.

## Device test
1. Keep app open, Start with VPN hint OFF, tap Test HTTP. This makes a genuine request through the proxy to a local HTTP origin and checks four binary bytes. Inspect the resulting session.
2. For browser traffic, record the current Wi-Fi proxy values. Configure this same Android device's Wi-Fi proxy to 127.0.0.1:8877 and browse an HTTP URL. Some clients ignore system proxy. Restore original settings BEFORE Stop or app exit; manual settings cannot be automatically restored by this app.
3. Alternatively test the optional VPN hint after explicit Android approval. The proxy is only a hint; HTTP traffic may not appear. Do not enable lockdown/always-on VPN for this preview. HTTPS bodies are not captured.
4. Stop, export SAZ/HAR to LOCAL device storage, transfer to Windows and verify Fiddler/DevTools. Android-produced exports and real-device operation require acceptance testing.
5. Capture is foreground-preview scope. Stop before leaving the app; service is not a durable headless Flutter engine. Process death may lose session metadata. Android UI body preview, full pagination, background capture, native TCP/IP engine, TLS MITM and release signing remain unimplemented.

## Build
Extract HTTP-Capture-Source.zip at repository root, overlay fixes then android-fixes. Generate Android runner with Flutter3.35.5: flutter create --platforms android --org dev.httpcapture --project-name capture_app --no-pub . (inside apps/capture_app); copy android-native files as in workflow. Set minSdk29. Java17 and Android SDK required. flutter analyze; flutter test; flutter build apk --debug.

## Licensing
Existing Dart/Flutter dependencies are reused. No third-party native packet engine is bundled. Existing dependency license inventory is not yet an Android APK compliance audit. Validate notices/native licenses and release signing before company deployment.
