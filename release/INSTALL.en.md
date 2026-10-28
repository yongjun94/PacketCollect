# HTTP Capture Preview — Installation

Development preview for Windows x64, macOS on Apple Silicon, and Android. No iOS or Intel Mac package is included. End users do not need to install Python or Flutter.

## Windows x64

1. Extract the entire `HTTP-Capture-Windows-x64.zip` archive into a new folder.
2. Run `HTTP-Capture.exe`. Keep its DLLs, `proxy`, `resources` and other bundled files together.
3. For HTTPS decryption, use the app's certificate settings to install this installation's CA with your consent.

This preview has no distribution code signature and may be blocked by company policy. Follow your organization's approval process; do not bypass security policy.

## macOS on Apple Silicon

1. Extract `HTTP-Capture-macOS-arm64.zip` and copy `HTTP-Capture.app` to Applications.
2. Click Start and approve the CA SSL trust and system proxy changes when prompted.
3. Check the CA trust status in Settings. After trust changes, reopen Safari if needed.
4. Use Stop before quitting to restore proxy settings. After a crash, reopen the app to attempt recovery.

The app is ad-hoc signed, without Developer ID signing or Apple notarization. Gatekeeper or managed policy may reject it. Execution approval must follow your organization's policy. Immediate proxy restoration after a forced termination or power loss is not guaranteed.

## Android

1. Download `HTTP-Capture-Android-preview.apk` to the device.
2. Review Android's permission request for the application used to install the APK, then install it.
3. Approve VPN access when requested by HTTP Capture.
4. To decrypt HTTPS, follow the app's instructions to save the public CA certificate and install it through Android's system settings with explicit user confirmation. Some apps do not trust user-installed CAs.

Application ID: `dev.httpcapture.capture_app.all`.

This APK uses a development/debug signing key. If an older APK has a different signing key, Android will reject an in-place update. Export important captures before considering uninstalling an older app; uninstalling can remove its local data and app-owned CA key. Stable release signing and update-key management are future distribution work.

## Validation and supported scope

The packages were obtained from successful CI builds of the same source commit. Windows/Mac build and automated checks passed. Android API35 emulator checks covered HTTP/HTTPS and proxy release after stopping or exiting. Physical-device compatibility and the Android user CA installation flow have not been comprehensively verified.

This tool captures proxy-aware HTTP/HTTPS traffic. It does not capture every TCP/UDP packet, bypass certificate pinning, or provide iOS standalone capture. Mac crash recovery has the limitations described above.

Captured/exported data may include cookies, tokens and customer information. Store and share it carefully. Packages do not include user captures or a shared deployment CA private key. The public CA is installation-specific; never share its private key.

`SHA256SUMS.txt` verifies the three executable packages. `build-provenance.json` records their CI origins. Checksums are an integrity check, not a code signature.
