# HTTP Capture

[한국어](README.md) | English

**A local HTTP/HTTPS capture tool with shared SAZ/HAR export for Windows, macOS and Android.** HTTP Capture focuses on collecting requests, responses and bodies for troubleshooting and evidence exchange. It is a development preview with platform-specific limitations, not an all-packet network monitor.

[Download apps](https://github.com/yongjun94/PacketCollect/releases/tag/v0.1.0-preview.20261028) · [Architecture & UI guide](docs/architecture.en.md) · [Installation](release/INSTALL.en.md) · [한국어 구조 안내](docs/architecture.ko.md)

## Downloads and first use

| Platform | Package | First steps |
|---|---|---|
| Windows x64 | `HTTP-Capture-Windows-x64.zip` | Extract all files, run the EXE, configure system-proxy capture and approve CA trust if HTTPS is required. |
| Apple Silicon Mac | `HTTP-Capture-macOS-arm64.zip` | Copy the app to Applications. Start prepares the listener and requests CA/proxy approval as needed. |
| Android | `HTTP-Capture-Android-preview.apk` | Install the APK, approve VPN access and complete Android's public CA installation steps for HTTPS. |

A GitHub account with access to this private repository is required. End users do not need Python or Flutter. Windows distribution signing and Mac Developer ID signing/notarization are not complete. Android uses debug signing; a different key can prevent updating an existing APK. Read the [installation guide](release/INSTALL.en.md) before replacing an older app or changing trust settings.

## Architecture at a glance

![HTTP Capture platform engines and shared layers](docs/images/architecture.svg)

Windows and Mac share the Flutter desktop screen, Python/mitmproxy engine and desktop packaging script. Their OS adapters differ. Android uses a separate Flutter screen, an in-process Dart proxy and Kotlin VPN/CA integration. **All three share `capture_core` for sessions/storage and `capture_export` for SAZ/HAR.**

The engine forwards traffic to the destination and produces capture events/body files. The UI saves common session metadata; exporters subsequently read that local store. Desktop control uses local stdio JSON messages, while Android uses Dart events and a native MethodChannel. This does not introduce an external analysis service.

| Source path inside `http-capture/` | Responsibility |
|---|---|
| `apps/capture_app/lib/main.dart` | Selects the Android or shared desktop screen |
| `apps/capture_app/lib/app.dart` | Shared Windows/Mac capture UI |
| `apps/capture_app/lib/android_app.dart` | Android capture and certificate workflow |
| `packages/capture_core` | Session model, SQLite metadata and body-file storage |
| `packages/capture_export` | Shared SAZ/HAR exporters and output finalization |
| `engines/desktop_proxy` | mitmproxy capture addon, local commands and Windows/Mac adapters |
| `engines/android_vpn` | Reviewed Kotlin VPN/CA sources and manifest |
| `scripts` | Build, test, Android runner generation and packaging |

The editable source is directly in `http-capture/`: no source ZIP or overlay-copy step is needed. Android's Flutter runner is generated from the pinned SDK without overwriting reviewed Dart source. [Read the full architecture guide](docs/architecture.en.md) for lifecycle, session fields, storage, exporter normalization, trust and recovery behavior.

## Desktop UI

![Desktop UI controls and session inspection](docs/images/desktop-ui.svg)

Start/Pause/Stop control capture; the status bar shows listener state and count. Filter searches method/URL/status metadata. Selecting a row opens Request/Response headers and a body preview. Settings contains port, HTTPS, CA and OS-proxy operations. Stop before Clear or Export.

The desktop preview reads at most the first 64 KiB of a body; export reads the stored body separately. In the current selected-session export dialog, **Continue exports the selected session and Cancel exports all sessions**. A one-entry HAR may therefore reflect export selection rather than the full capture.

## Android UI

![Android UI and VPN capture workflow](docs/images/android-ui.svg)

Configure optional HTTPS, complete the user CA process, then Start and approve VPN use. Switch to the target app and trigger new requests. Return, Stop and export through the system document picker. Switching apps keeps capture active. Stop releases the VPN proxy before the local listener closes.

This VPN advertises a temporary HTTP proxy; it does not contain a full TCP/UDP packet-processing stack. Proxy-aware apps are the capture target. The mobile list currently displays up to 200 filtered stored sessions; details show headers and body size. `Test HTTP`/`Test TLS` exercise local test origins and do not prove that every external app is captured.

**The UI images are source-based documentation schematics, not runtime screenshots. All example sessions and sizes are synthetic.**

## Data, export and privacy

`CaptureSession` records request/optional response, timestamps, source, capture state/errors and body references. Metadata is in SQLite; binary bodies are separate local files. The common model allows duplicate header entries, although Android's parsed API cannot preserve every original casing/order detail.

SAZ is a ZIP of message files and XML metadata. Its HTTP representation normalizes framing and maps HTTP/2 start lines to HTTP/1.1 with original metadata retained. HAR 1.2 records standard fields plus capture-specific status/raw-content extensions; complete gzip can be decoded for content, while other encodings are not all decoded into a browser-ready representation. This is not a byte-for-byte TLS/TCP wire recording.

Captured data can contain cookies, credentials and customer information. There is no automatic redaction or cloud synchronization. User-directed export can select a destination outside the app; Android document providers may include cloud locations. Local capture does not make the resulting archive safe to share indiscriminately.

## Validation and limitations

- [Windows](https://github.com/yongjun94/PacketCollect/actions/runs/40652755920) and [Mac](https://github.com/yongjun94/PacketCollect/actions/runs/40652755909): source-cleanup builds and automated checks passed.
- [Android](https://github.com/yongjun94/PacketCollect/actions/runs/40652755751): APK build and API35 emulator HTTP/HTTPS/lifecycle checks passed. Physical-device CA installation needs separate verification.
- Earlier Windows capture/Fiddler/DevTools imports were user-confirmed. A user-provided Mac HAR confirmed Safari HTTPS response/body capture. These do not validate every new build on every device.
- Apps ignoring proxies, pinned TLS, bypass rules, enterprise proxy/VPN configurations and unsupported protocols may limit visibility. WebSocket payloads, HTTP/3/QUIC, iOS standalone capture, Intel Mac packages and remote-capture UI are outside this preview's supplied scope.
- Mac forced-termination recovery is not immediate or guaranteed. Reopening the app attempts journal-based restoration; existing externally changed settings are protected.

## Developing and maintaining

Use Flutter 3.35.5/Dart 3.9.2 and Python 3.12.x as defined by the project. Desktop builds run `scripts/build_desktop.py windows` or `macos` on the target OS. Android starts with `scripts/prepare_android.py`, then Flutter analyze/test/build in the app directory. [Build commands](http-capture/README.md), [code map](docs/code-map.md) and [CI workflows](.github/workflows) are the executable references.

Desktop UI/IPC tests live in `test/desktop`; Android engine/UI tests live in `test/android`. Common exporter tests stay with the package. Keep OS routing/trust operations in adapters and format changes in the shared exporter, rather than creating platform copies.

Preview releases use successful same-source CI artifacts listed in `release/preview.json`, verify the payloads and publish a complete draft with checksums/provenance. English release text and setup instructions live in `release/notes.en.md` and `release/INSTALL.en.md`. Release signing/update keys, broader real-device acceptance, enterprise upstream support and optional redaction remain future work.
