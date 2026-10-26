# Apple Silicon macOS preview

This is a native arm64, direct-distribution development build. The app is ad-hoc signed, not Developer ID signed or notarized. App Sandbox is disabled to support the bundled child process and user-selected local exports. Do not disable Gatekeeper globally; use your organization-approved execution policy.

## Scope
Common Flutter UI, SQLite/body storage, local HTTP/HTTPS proxy and SAZ/HAR exporters. macOS automatic certificate installation/removal and system proxy changes are NOT implemented. The app clearly labels manual configuration.

## Manual acceptance
1. Open Settings before capture and reveal the public CA certificate. Import only mitmproxy-ca-cert.pem into Keychain Access. Compare SHA-256 fingerprint with the app and explicitly configure SSL trust if approved. Never copy mitmproxy-ca.pem or any private key.
2. Start capture. Configure the test client's HTTP and HTTPS proxy to 127.0.0.1:8877 (or the configured port). If using macOS network settings, record the original values and restore them before Stop, after a crash, or before closing the app. Automatic recovery is unavailable in this preview. Do not override managed proxy/PAC configuration.
3. Browse HTTP and HTTPS pages and inspect response bodies. Test redirects, JSON, binary and failed requests.
4. Restore any manually changed system proxy settings, then stop capture and export HAR and SAZ. Import HAR in Chrome DevTools on Mac and transfer SAZ to Windows for Fiddler Classic import.
5. Remove only this installation's CA in Keychain Access after testing; identify it by fingerprint, not just its generic name.

Native engine smoke tests do not modify Keychain or system proxy. A successful build does not prove GUI, Safari/Chrome trust or importer compatibility on a real Mac.

Windows acceptance: user reported normal Windows operation and confirmed Fiddler and DevTools import on 2026-10-26. macOS manual acceptance remains pending.
