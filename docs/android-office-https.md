# Android HTTPS compatibility investigation

Excel and Copilot reach the CONNECT proxy, work when interception is off, and fail when interception is on. A browser succeeds on the same device. This narrows the problem to interception, but does not prove certificate pinning.

## Changes
- TLS terminates on a raw loopback socket relayed from CONNECT. HTTP-owned detached sockets cannot be upgraded directly. The returned handshake exception is retained in session TLS metadata instead of a generic "check trust/pinning" message.
- Advertise HTTP/1.1 explicitly using ALPN. The parser does not implement HTTP/2, and does not advertise h2.
- Separate certificate-generation, client-tls-handshake, client-http, and upstream-or-http failures.
- Tunnel sessions are not marked with an error. Missing response content is displayed as not captured, not as a measured zero-byte server response.
- Keep upstream certificate validation enabled. No automatic retry without decryption, no certificate-pinning bypass, and no global certificate validation suppression.

## Validation
Automated real-socket tests cover decrypted binary bodies, all-host mode, ALPN selection, client CA rejection, untrusted upstream rejection, and unchanged encrypted tunneling. Local validation on Dart 3.9.2/Linux passed all six HTTPS socket cases and two existing HTTP forwarding cases. Static analysis of the engine passed. The Android build workflow also passed flutter analyze and its test suite; APK build and API35 emulator results are recorded below when complete.

**Excel/Copilot real-device HTTPS capture remains unverified.** The ALPN/handshake changes are compatibility and diagnostic improvements, not evidence that Office trust restrictions have been resolved. A trusted test client is not a substitute for Office testing.

## Device check
1. Stop capture, install the candidate, and check this installation's CA fingerprint. If an APK update requires uninstalling because signing keys differ, export needed captures first. Uninstalling loses the local CA key and requires the new CA to be installed.
2. Enable HTTPS decryption and confirm a browser captures real GET/POST requests and response bodies.
3. Reproduce Excel/Copilot separately. Open the CONNECT session and inspect TLS failureStage and detail. HAR exports retain the failure description in _error; structured TLS metadata is displayed in the app and stored in SQLite, not exported as a HAR TLS field.
4. Check that Office and the installed CA are in the intended Android profile. An OS CA store check does not prove another app trusts that CA.
5. If client-tls-handshake fails, preserve the actual TLS error and app/Android versions for investigation. A generic alert does not prove pinning. If a released app refuses interception, an HTTP Capture change alone cannot guarantee decryption.
6. Stop capture to release the temporary VPN proxy.

Do not publish capture archives containing credentials or customer data. Logs displayed in the app remain local; export is explicit.

## Verified candidate — 2026-10-29
- Runtime source: `293200114fc1f6649085a09645bea3c23ec94335`.
- Compile/analyze/test run: https://github.com/yongjun94/PacketCollect/actions/runs/40801378048 (flutter analyze passed; all 13 Flutter tests passed; APK compiled. The original overall run failed on emulator navigation, not the compile/test steps.)
- Exact-APK API35 device retest: https://github.com/yongjun94/PacketCollect/actions/runs/40803872316 — **passed**.
- The retest checks the source run, completed analysis/build steps, artifact ID, and exact APK SHA-256 before installation. The test harness waits for the asynchronous Security Settings launch and retries missed settings-navigation taps.
- Artifact: `12866217006`; APK bytes: `158806012`.
- APK SHA-256: `a0b1235434ffe5479bcd734125123128d634a058e8b17430c1e5118611ba20fd`.
- Emulator passed: app launch, foreground service, HTTP binary forwarding, sessions, HAR document picker, body persistence, VPN proxy installation, Stop restoration, background capture, Back exit restoration, force-stop restoration, HTTPS all-host switch, public CA export, local HTTPS binary forwarding, and rejection of an untrusted upstream.
- Manual user CA installation and real-device Office/Copilot HTTPS capture: **not verified by these tests**.

## 한국어 안내
이 버전은 Android HTTPS 협상과 오류 진단을 개선한 후보 버전입니다. Excel·Copilot이 사용자 CA를 거부하는 경우까지 해결됐다고 확인한 것은 아닙니다.

1. 필요한 기존 캡처를 내보낸 뒤 APK를 업데이트합니다. 서명 차이 때문에 삭제 후 설치해야 한다면 로컬 데이터와 기존 CA 개인키가 삭제됩니다. 새 설치본의 공개 CA를 다시 설치해야 합니다.
2. HTTPS 설정에서 복호화를 켜고 Excel·Copilot을 완전히 종료한 뒤 다시 실행합니다.
3. 새 세션의 TLS 항목에서 `failureStage`와 `detail`을 확인합니다. 브라우저 HTTPS 성공만으로 Office 앱의 인증서 신뢰까지 확인되는 것은 아닙니다.
4. 복호화를 끄면 터널 연결을 그대로 전달하며, 응답은 “0 bytes” 대신 “응답 내용 미수집”으로 표시됩니다.

`Test TLS`는 앱 자체의 로컬 TLS 수집 경로 검증입니다. Office가 캡처용 CA를 신뢰하는지 검사하는 기능은 아닙니다.
