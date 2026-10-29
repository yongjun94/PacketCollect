## English — Desktop-only preview

**Active development, support and distribution cover Windows and macOS only as of 2026-10-29.** Android development/APK distribution is discontinued; iOS is unsupported. Any APK and old attached installation guide remaining in historical assets do not define current support.

| Download | Platform |
|---|---|
| HTTP-Capture-Windows-x64.zip | Windows x64 |
| HTTP-Capture-macOS-arm64.zip | Apple Silicon macOS |

[Current installation guide](https://github.com/yongjun94/PacketCollect/blob/main/release/INSTALL.en.md) · [Support policy and mobile rationale](https://github.com/yongjun94/PacketCollect/blob/main/docs/platform-support.md) · [Architecture and UI](https://github.com/yongjun94/PacketCollect/blob/main/docs/architecture.en.md)

Browser capture worked on Android, but Office HTTPS decryption could not be verified. This project now focuses on desktop. It does not claim all mobile capture is impossible or every desktop app can be decrypted.

HTTP Capture is independent of Progress/Telerik and was started in response to Fiddler Classic's commercial-use policy changes. Classic's non-commercial free use is distinct.

The desktop packages come from successful same-source CI builds. Earlier user evidence includes Windows Fiddler/DevTools imports and Mac Safari HTTPS capture; it does not establish universal app or later-build compatibility. Source: `{{SOURCE_SHA}}`.

End users do not need Python or Flutter. Windows distribution signing and Mac Developer ID signing/notarization remain incomplete. Follow organizational policy. Capture covers proxy-aware HTTP/HTTPS; exports can contain sensitive information.

Existing binaries, checksums and provenance are preserved. Third-party license review remains incomplete; technical tests are separate from redistribution compliance.
