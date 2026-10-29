> **과거 Android 실험 기록 / Historical Android experiment.** 2026-10-29부터 개발·지원·APK 배포를 중단했습니다. 아래 내용은 현행 설치·사용 안내가 아니며 Office HTTPS 복호화 성공을 뜻하지 않습니다. [현재 지원 정책 / Current policy](../../docs/platform-support.md)

# Android all-host HTTPS preview

HTTPS decryption is opt-in and applies to all proxy-aware CONNECT hosts, without a host list. Apps rejecting user CAs, pinned certificates, HTTP/3, client certificates, and proxy-bypassing traffic remain unsupported and may fail while interception is enabled; turn decryption off and restart capture.

Certificate preparation writes the public CA to Downloads using Android MediaStore and opens security settings. Android 11+ requires manual installation through system settings; Android 10 opens the user-confirmed installer. Certificate/private key remain per-app, generated via Android Keystore; installing this separate debug preview requires its own CA. Remove the corresponding user CA manually by fingerprint when no longer required. Real-device CA installation remains pending.

Stop/Back exit/force-stop release the VPN proxy; switching apps keeps capture active. No Wi-Fi proxy writes. No root, device owner, pinning bypass, or system CA modification. App ID dev.httpcapture.capture_app.all preserves data in previous previews; it uses debug signing and is not a production release.

Upstream server certificates remain verified against default trusted roots. HTTP/1.1 parsed headers may be normalized, each body is capped at 64 MiB, and there is no full packet-level TCP/UDP capture. SAZ/HAR use the existing common exporters.
