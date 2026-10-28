## English — Windows, macOS and Android downloads

HTTP Capture is a local HTTP/HTTPS capture tool with SAZ and HAR export. Download the file for your platform from **Assets** below. A GitHub account with access to this private repository is required.

| Download | Platform | Installation |
|---|---|---|
| `HTTP-Capture-Windows-x64.zip` | Windows x64 | Extract the entire archive and run `HTTP-Capture.exe`. |
| `HTTP-Capture-macOS-arm64.zip` | macOS on Apple Silicon | Extract the archive and copy `HTTP-Capture.app` to Applications. |
| `HTTP-Capture-Android-preview.apk` | Android | Install the APK and approve the VPN permission when requested. |

End users do not need Python or the Flutter SDK. See **INSTALL.en.md** for HTTPS CA setup, installation details and Android update precautions.

### Preview status and signing

This is a development preview. Windows has no distribution code signature. The Mac app is ad-hoc signed, without Developer ID signing or Apple notarization. Android uses a debug signing key; an existing APK signed with a different key cannot be updated in place. Back up captured data before considering removal of an older app. Follow your organization's execution and installation policies.

### Validation and limitations

All three packages come from successful CI runs of the same source commit. Windows and Mac build/automated checks passed. Android API35 emulator checks passed for HTTP/HTTPS, capture lifecycle and proxy release on stop/exit. These results do not establish compatibility with every physical device or application; Android user CA installation still requires manual verification.

Capture covers proxy-aware HTTP/HTTPS traffic, not every TCP/UDP packet. Certificate pinning is not bypassed. iOS standalone capture and Intel Mac packages are not included. On macOS, immediate proxy recovery after a forced termination is not guaranteed; reopening the app attempts recovery.

Source commit: `{{SOURCE_SHA}}`.

Use **SHA256SUMS.txt** and **build-provenance.json** to check package integrity and CI provenance. Checksums do not replace code signing.
