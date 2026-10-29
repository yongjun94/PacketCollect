# HTTP Capture Preview — Installation

> **Desktop-only support since 2026-10-29.** Any APK or attached installation guide in an older release is historical and unsupported. This repository guide is current. [Support policy](../docs/platform-support.md)

Development preview for Windows x64 and macOS on Apple Silicon. Android/iOS and Intel Mac packages are outside the current scope. End users do not need to install Python or Flutter.

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

## Validation and supported scope

The packages were obtained from successful CI builds of the same source commit. Windows/Mac build and automated checks passed. Physical-device and application compatibility have not been comprehensively verified.

This tool captures proxy-aware HTTP/HTTPS traffic. It does not capture every TCP/UDP packet, bypass certificate pinning, or provide iOS standalone capture. Mac crash recovery has the limitations described above.

Captured/exported data may include cookies, tokens and customer information. Store and share it carefully. Packages do not include user captures or a shared deployment CA private key. The public CA is installation-specific; never share its private key.

`SHA256SUMS.txt` verifies the original release packages. `build-provenance.json` records their CI origins. Checksums are an integrity check, not a code signature.
