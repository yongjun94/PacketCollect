# Android HTTPS preview

Adds opt-in TLS interception for exact user-selected hosts. A separate dev.httpcapture.capture_app.https package preserves Safe Preview data; CI debug signing is not a production release key. Do not run both captures at once.

Stop/Back exit/force-stop release the VPN proxy; Home/app switching keeps it alive. No Wi-Fi proxy writes. No root, device owner, pinning bypass or system CA changes.

## Use
Open HTTPS settings while stopped. Save the public CA certificate to local storage. Android 11+ requires the user to install it in Settings > Security > Install certificate > CA certificate. Match the SHA-256 fingerprint. Return to HTTPS settings to refresh store status. Enable HTTPS decryption and enter exact hosts separated by commas, without schemes, ports or wildcards. Apply, then Start and approve the VPN. Other hosts use encrypted CONNECT tunneling. Apps which ignore the proxy, reject user CAs, use pinning, HTTP/3, client certificates or WebSockets may not work with interception. Remove those hosts from the allowlist to restore tunneling. Settings are intentionally opt-in again after app restart.

Remove only this CA in Android user credentials by matching the fingerprint. App uninstall does not necessarily remove a user-installed CA. The application never silently installs/removes trust. Capture stop releases the proxy, but leaves the user-approved CA installed.

## Implementation
Root RSA key generated in Android Keystore; non-exportable, not included in APK, no cloud backup. Root certificate has CA pathLen=0 and keyCertSign/cRLSign; host certificates have SAN and serverAuth, seven-day validity. Leaf keys exist only in app memory/IPC and are not exported. Bouncy Castle bcpkix-jdk15to18 1.86 (and bcprov/bcutil transitives) constructs certificates; TLS is Dart dart:io. Upstream certificates/hostnames are verified with the default trust context in production; there is no accept-all callback. Only the explicit loopback self-test trusts the test origin CA. Parsed HTTP/1.1 headers retain duplicate values but not original global order/casing. Body capture limit 64 MiB per side. No HTTP/2, HTTP/3, packet TCP/UDP engine, or WebSocket capture in this variant. Per-connection loopback TLS listener, a concurrency guard targeting 64 simultaneous interceptions; performance not benchmarked.

## Validation
CI performs TLS proxy tests: binary POST/response capture, client rejects untrusted CA, upstream rejects untrusted origin, tunnel-only mode. Emulator self-test creates device-local HTTPS origin with generated CA, checks decrypted request/response and HAR base64, and confirms untrusted upstream rejection. Existing VPN cleanup/regression checks remain. Real-device CA installation, browser/app capture, and this variant's Fiddler/DevTools imports require manual acceptance. Do not equate the self-test with system/browser CA trust validation.
