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


## Architecture, UI and operation guide

[Read the illustrated architecture and UI guide](https://github.com/yongjun94/PacketCollect/blob/main/docs/architecture.en.md) · [한국어 상세 안내](https://github.com/yongjun94/PacketCollect/blob/main/docs/architecture.ko.md)

### How the platforms fit together

| Platform | UI and capture engine | Shared modules |
|---|---|---|
| Windows / macOS | One Flutter desktop screen and bundled Python/mitmproxy process, with OS-specific proxy/CA adapters | Dart session model, SQLite/body storage and SAZ/HAR exporters |
| Android | Separate Flutter screen, Dart HTTP/TLS proxy and Kotlin VPN/CA integration | The same Dart session model, store and exporters |

The engine forwards requests to the destination and writes body files/session events. The UI records metadata in the local store; exporters read the stored sessions to produce files. Desktop control uses local stdio JSON messages. Android native operations use a MethodChannel. No external AI or analysis service is involved.

### Interface previews

- [Desktop UI diagram](https://github.com/yongjun94/PacketCollect/blob/main/docs/images/desktop-ui.svg): capture toolbar, connection state, filtered session table, Request/Response inspector and Settings.
- [Android UI diagram](https://github.com/yongjun94/PacketCollect/blob/main/docs/images/android-ui.svg): HTTPS setup, VPN approval, app switching, Stop and export.
- [Whole-system diagram](https://github.com/yongjun94/PacketCollect/blob/main/docs/images/architecture.svg): platform engines and the shared Dart pipeline.

These are documentation schematics based on the source, with synthetic session values—not runtime screenshots or performance measurements. They do not imply an unimplemented app/process selector or packet view.

### Reading a capture

A green Capturing status means the listener is running; it does not prove that a particular app uses it. Trigger a fresh request and look for new URL/method/status/body data. A decrypted HTTPS GET/POST plus response content is stronger evidence than CONNECT alone. User-Agent is only a clue, not reliable process attribution.

Stop before export. In the current desktop selection dialog, Continue exports only the selected session; Cancel exports all stored sessions. On Android, the list shows up to 200 filtered stored sessions, while exports iterate the stored capture. The desktop body preview is limited to the first 64 KiB; Android details show headers/body size.

The detailed guide explains model fields, body completeness, gzip/raw-content HAR extensions, SAZ HTTP/2 normalization, CA consent, proxy ownership/recovery, test evidence and remaining work.
