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
CI build, Flutter tests, actual Android Keystore issuance, OpenSSL validation, and API35 emulator lifecycle results will be recorded after execution. Excel/Copilot real-device acceptance is unverified.
