# Android certificate identifier compatibility candidate

The uploaded public CA lacked Subject Key Identifier (SKI). Its self-signature and basic CA fields verified in OpenSSL; that alone did not prove Office trust or make SKI the confirmed cause of the observed certificate_unknown alerts.

## Implementation
- New roots contain non-critical SKI and AKI. Root AKI identifies the same public key as SKI.
- Every new server certificate contains non-critical SKI/AKI, matching DNS/IP SAN, serverAuth EKU, and validity bounded by the issuer.
- Each leaf is checked on-device before use: signature, validity, SAN, key usage, EKU, identifiers, and PKIX path with an explicit local test anchor.
- Existing roots are preserved. A legacy-CA upgrade requires explicit app UI confirmation and a stopped capture service. It reissues the public CA with the same non-exportable Android Keystore key, retains a public copy of the previous root, writes through AtomicFile, clears cached identities, and disables interception until the user configures it again.
- Android certificate-store installation/removal remains a manual user-approved OS operation.
- Test TLS now also checks issuance for four Office-related DNS names, IPv4, and IPv6. These are generated certificate checks, not requests to Microsoft services or proof that Office accepts the CA.
- Debug builds persist public certificate evidence and a report only; the verification evidence excludes all private keys. The existing app-local leaf-key IPC is unchanged. The CA key never leaves Android Keystore.
- The emulator pulls the public evidence and uses independent OpenSSL strict chain/hostname verification, including negative hostname and missing-trust-anchor checks.
- No server-certificate validation suppression, pinning bypass, or automatic non-decrypting retry is added.

## Device retest
1. Export needed captures before replacing an APK if the debug signing key requires uninstall/reinstall.
2. On a fresh install, the new CA already contains SKI/AKI. On an in-place upgrade, HTTPS settings shows CA 규격 업데이트 only for an old profile. Confirming it changes the CA fingerprint and requires installation of the new public certificate; remove only the old HTTP Capture CA you recognize.
3. Use 인증서 준비 및 설정 열기 to install the new public CA, then check its fingerprint/status and enable decryption.
4. Run Test TLS; then reproduce Excel and Copilot separately and export a new HAR.
5. If client-tls-handshake certificate_unknown persists, certificate profile compliance has not resolved the app's rejection. Determine app trust policy from client-side diagnostics. Do not equate a successful local test with Office acceptance.

## Validation status
Verified on 2026-10-29:
- Source: `7f9d2f81e5d22a27c4f2f56017c14242d5a63497`.
- CI: https://github.com/yongjun94/PacketCollect/actions/runs/40818598999 — **success**.
- Flutter analyze: no issues. Flutter tests: **15 passed**, including confirmation cancel/approve behavior.
- APK build: passed. Artifact `12874015862`; APK bytes `158824192`.
- APK SHA-256: `f16a5e37ef7894fee83d7f12aac5e2d50a94bccbad0896198bb7b4aaa56a1951`.
- API35 x86_64 emulator: actual Android Keystore issuance and PKIX verification passed for all six DNS/IP names; native rejection of unconsented CA upgrade and unchanged CA bytes passed.
- Independent OpenSSL strict chain, server-auth purpose, DNS/IP identity verification, incorrect-hostname rejection and missing-trust-anchor rejection passed.
- Device HTTP/HTTPS binary round trips, untrusted upstream rejection, HAR picker, body persistence, background capture and Stop/Back/force-stop proxy release passed.
- Test evidence: `Android-test-diagnostics` artifact `12874185736`, containing public certificates and `android-certificate-profile.json`.
- These checks explicitly trust the local test CA. Android user CA installation, real-device legacy CA replacement and Excel/Copilot acceptance remain **manual/unverified**. No Office app was run in CI.

## 한국어 재확인
1. 필요한 캡처를 백업하고 수정 APK를 설치합니다. 서명 차이로 삭제 후 재설치하면 새 CA가 생성되므로 다시 설치해야 합니다.
2. 새 설치에서는 SKI/AKI가 포함된 CA가 자동 생성됩니다. 기존 설치를 업데이트한 경우 HTTPS 설정의 **CA 규격 업데이트**가 보이면 내용을 확인하고 승인합니다.
3. 이전 HTTP Capture CA만 제거하고, **인증서 준비 및 설정 열기**로 새 공개 CA를 설치합니다. 앱의 SHA-256과 설치한 인증서 지문을 확인합니다.
4. **Test TLS**를 실행한 뒤 복호화를 켜고 Excel·Copilot을 완전히 종료 후 재실행합니다.
5. 실제 Office 요청이 GET/POST 및 응답으로 기록되는지 확인합니다. CONNECT의 certificate_unknown 오류만 남으면 규격 보완으로 앱의 인증서 거부가 해결되지 않은 것입니다.
