# HTTP Capture

[한국어](README.md) | English

HTTP Capture is a local HTTP/HTTPS capture project for Windows, macOS and Android, with Fiddler-compatible SAZ and HAR export. It is a development preview, not a fully validated product on every platform.

## Downloads

[Download the preview release](https://github.com/yongjun94/PacketCollect/releases/tag/v0.1.0-preview.20261028): Windows x64 ZIP, macOS Apple Silicon ZIP and Android APK. This repository is private; a GitHub account with repository access is required. See the release's `INSTALL.en.md` for installation and CA setup.

End users do not need Python or Flutter. Windows distribution signing and Mac Developer ID signing/notarization are not complete. Android uses debug signing; different signing keys may prevent in-place updates. Back up captures before removing an older app.

## Source structure

The editable project is in **`http-capture/`**. Builds use these files directly; there is no source-ZIP extraction or platform overlay step.

| Path inside `http-capture/` | Responsibility |
|---|---|
| `apps/capture_app` | Flutter UI and platform integration |
| `packages/capture_core` | Shared session model, SQLite metadata and body-file storage |
| `packages/capture_export` | Shared SAZ/HAR exporters |
| `engines/desktop_proxy` | Python/mitmproxy engine and Windows/Mac OS adapters |
| `engines/android_vpn` | Android VPN/CA Kotlin sources and manifest |
| `scripts` | Build, test and packaging tools |

Windows and Mac share the desktop UI, engine and build script. Android has a separate UI and Dart proxy with Kotlin VPN/CA integration, while reusing the common model, storage and exporters. Its Flutter Android runner is generated from the pinned SDK; reviewed Kotlin sources are kept in `engines/android_vpn`. iOS standalone capture is not implemented.

[Build commands](http-capture/README.md) and the [code map](docs/code-map.md) are currently in Korean. The platform CI workflows in [`.github/workflows`](.github/workflows) define the executed build and test steps. Earlier ZIP/overlay versions remain in Git history and are not the current source layout.

## Validation and limitations

Windows/Mac builds and automated checks passed after the source-tree cleanup. Android APK builds and API35 emulator HTTP/HTTPS/lifecycle checks passed. Physical-device behavior and manual CA installation need separate verification. The earlier Windows version was user-checked with Fiddler and DevTools; a user-provided Mac HAR confirmed Safari HTTPS response capture.

Capture is limited to proxy-aware HTTP/HTTPS traffic, not all TCP/UDP packets. Certificate pinning is not bypassed. Captures and exports remain local unless the user explicitly shares or exports them to another destination. They can contain credentials and personal data; automatic redaction is not implemented.

## Preview publishing

Maintainers specify successful same-commit CI runs and artifact IDs in `release/preview.json`. On a main-branch update to that file, the release workflow validates the artifacts, uploads a draft, verifies every asset, then publishes a prerelease with checksums and provenance. New versions use new tags; existing releases are not overwritten. English release text and installation instructions are maintained in `release/notes.en.md` and `release/INSTALL.en.md`.
