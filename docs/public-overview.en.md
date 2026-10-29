# HTTP Capture — Public overview

HTTP Capture is an independent Windows/macOS desktop HTTP/HTTPS capture and SAZ/HAR export project, started in response to Fiddler Classic's commercial-use policy changes. It is not affiliated with Progress/Telerik. Classic's non-commercial free use is distinct from commercial-use policy. [Official notice](https://www.telerik.com/fiddler/fiddler-classic/commercial-use)

![Desktop architecture](images/architecture.svg)

Windows and Mac share the Flutter UI, bundled Python/mitmproxy, common Dart sessions, SQLite/body storage and SAZ/HAR exporters. OS proxy/CA adapters differ. Capture, pause, stop, basic filtering, request/response inspection and export are provided.

Android development/APK distribution was discontinued on 2026-10-29 after Office HTTPS decryption could not be verified despite working browser capture. iOS is unsupported. This is a scope decision, not a claim that all mobile capture is impossible.

Capture covers proxy-aware HTTP/HTTPS, not every packet or application. Storage is local with no automatic AI/cloud upload. Exports may contain sensitive information.

User evidence includes Windows Fiddler/DevTools imports and a Mac Safari HTTPS HAR, not universal compatibility. mitmproxy itself is MIT-licensed; the whole bundle is not. LGPL/MPL obligations, the project's own license, distribution compliance and signing/notarization remain under review.

[Support policy](platform-support.md) · [Architecture](architecture.en.md) · [Desktop UI schematic](images/desktop-ui.svg) · [License review](license-review-status.md)
