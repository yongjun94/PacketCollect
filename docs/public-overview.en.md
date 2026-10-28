# HTTP Capture — Public-facing project overview

> Draft project description prepared for publication. It does not make the repository public, grant a license to the project's own code, or certify binary-distribution compliance.

## Overview and motivation

HTTP Capture is an independent project that records local, proxy-aware HTTP/HTTPS requests and responses on Windows, macOS and Android and exports them as SAZ/HAR files. It focuses on capture and portable troubleshooting evidence.

The project was started in response to changes in Fiddler Classic's business/commercial-use licensing and the move of affected users to the commercial Fiddler Everywhere offering. Classic remains free for non-commercial use. [Official transition notice](https://www.telerik.com/fiddler/fiddler-classic/commercial-use)

This project is not an official Fiddler distribution and is not affiliated with Progress/Telerik.

## Architecture

![Platform capture engines and shared Dart layers](images/architecture.svg)

| Component | Role |
|---|---|
| Flutter UI | Desktop session inspection and Android VPN/CA workflows |
| Desktop capture | Bundled Python/mitmproxy process with Windows/Mac OS adapters |
| Android capture | Dart local HTTP/TLS proxy with Kotlin VPN/CA integration |
| Capture Core | Shared session model, SQLite metadata and body files |
| Capture Export | Shared Dart SAZ/HAR generation |

Windows and Mac share their desktop screen and engine. Android uses a separate UI and capture implementation while reusing the common model, storage and exporters.

## Features and interface

The preview records requests/responses, headers, bodies, capture state and errors. It provides explicit-consent local CA operations, eligible HTTPS decryption, basic session filtering, inspection and file export. Routing adapters provide stop/exit cleanup and documented recovery paths.

[Desktop UI diagram](images/desktop-ui.svg) · [Android UI diagram](images/android-ui.svg)

These source-based documentation schematics use synthetic data. They are not customer captures or runtime screenshots.

## Validation and boundaries

Windows x64, Apple Silicon Mac and Android builds/automated checks passed after the common source-tree cleanup. Android API35 emulator checks covered HTTP/HTTPS and VPN proxy release on stop/exit. Earlier Windows Fiddler/DevTools imports were user-confirmed; a user-provided Mac HAR also demonstrated Safari HTTPS response capture. These results do not validate every new build on every physical device or application.

This is not a full TCP/UDP packet sniffer. Apps ignoring proxies, user CA restrictions, certificate pinning, bypass rules and corporate policies can limit capture. The current Android VPN advertises a temporary HTTP proxy rather than implementing a general packet-processing stack. iOS standalone capture, HTTP/3, WebSocket payload capture and remote-capture UI are not supplied by this preview.

## Data and licensing status

Captures are stored locally, without automatic AI-service uploads or cloud synchronization. A user-selected export destination may be remote. Captures can contain credentials, cookies and personal information; automatic redaction is not implemented.

mitmproxy itself is MIT-licensed, but the entire binary bundle is not a single MIT-licensed work. Desktop packages contain dependencies with LGPL, MPL and other terms. Notices and SBOMs are evidence for review, not a distribution approval. The project's own top-level license and third-party source/recombination requirements remain under review. Current binaries are technical previews and must not be treated as cleared for broad external redistribution.

[License review status](license-review-status.md) · [Publication checklist](publication-checklist.md) · [Full architecture guide](architecture.en.md)
