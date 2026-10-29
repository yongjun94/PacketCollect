# HTTP Capture

[한국어](README.md) | English

**A local HTTP/HTTPS capture and SAZ/HAR export tool for Windows and macOS desktops.**

> As of 2026-10-29, active development and distribution are desktop-only. Android development/APK distribution is discontinued; iOS is unsupported. [Support policy and rationale](docs/platform-support.md)
>
> Third-party license review remains incomplete. These are technical previews, not packages cleared for broad external redistribution. [Review status](docs/license-review-status.md)

## Supported platforms and downloads

| Platform | Current scope |
|---|---|
| Windows x64 | Flutter desktop UI and bundled Python/mitmproxy |
| Apple Silicon macOS | The same UI/engine with macOS proxy and Keychain adapters |
| Android / iOS | Outside current development, support and distribution |

[Desktop preview downloads](https://github.com/yongjun94/PacketCollect/releases/tag/v0.1.0-preview.20261028) · [Installation](release/INSTALL.en.md)

Any Android APK remaining in an older release is an unsupported historical experiment. End users do not need Python or Flutter. Extract the complete desktop archive. Windows distribution signing and Mac Developer ID signing/notarization are incomplete.

## Why this project exists

HTTP Capture was started as an **independent response to changes in Fiddler Classic's business/commercial-use licensing and the requirement for affected users to move to the paid commercial offering, Fiddler Everywhere**. The goal is a local tool focused on HTTP/HTTPS collection and SAZ/HAR export for workplace troubleshooting and customer support.

More precisely, Fiddler Classic did not become a paid product for every user. Progress announced the change on August 3, 2026, with a September 17, 2026 transition deadline for commercial users. Classic remains free for non-commercial use; business/commercial users are directed to Fiddler Everywhere under a commercial license. [Official transition notice](https://www.telerik.com/fiddler/fiddler-classic/commercial-use) · [Official EULA](https://www.telerik.com/purchase/license-agreement/fiddler-enterprise-support)

HTTP Capture is not an official Progress/Telerik product, fork or affiliated project. SAZ support is independently implemented. This motivation does not imply bypassing Fiddler licensing or feature parity with the Fiddler product family.

## Architecture and operation

![Desktop architecture](docs/images/architecture.svg)

Windows and Mac share `app.dart`, `desktop_engine.dart`, the Python/mitmproxy engine, `capture_core` session/storage code and `capture_export` SAZ/HAR exporters. Only OS proxy/CA operations use separate adapters. Editable source lives directly in `http-capture/`.

![Desktop UI schematic](docs/images/desktop-ui.svg)

Review port, HTTPS, CA trust and system-proxy settings, then Start. Trigger a fresh request, inspect new sessions, Stop and export SAZ/HAR. Check the system-proxy option on Windows; Mac Start requests CA/proxy approval when needed. These UI images are source-based schematics with synthetic data, not runtime screenshots.

Capture covers **proxy-aware HTTP/HTTPS**, not every TCP/UDP packet. Untrusted interception CAs, certificate pinning, proxy bypass and enterprise policy can also limit desktop capture. Data is stored locally; exported archives can contain tokens, cookies and personal information.

## Development and validation

- [Build commands](http-capture/README.md)
- [Architecture and UI](docs/architecture.en.md)
- [Code map](docs/code-map.md)
- [Support policy and validation limits](docs/platform-support.md)
- [Windows/Mac CI](.github/workflows)

The user confirmed Windows capture and Fiddler Classic SAZ/Chrome DevTools HAR imports on an earlier build. A user-supplied Mac HAR confirmed Safari HTTPS response storage. These observations and CI checks do not establish compatibility with every app or subsequent build.

Mobile source and test records are retained as historical experiments. Android workflows have been moved out of the active workflow directory. Future development and releases focus on Windows and macOS.
