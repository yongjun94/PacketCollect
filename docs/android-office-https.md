# Android HTTPS compatibility investigation

Excel and Copilot reach the CONNECT proxy, work when interception is off, and fail when interception is on. A browser succeeds on the same device. This narrows the problem to interception, but does not prove certificate pinning.

## Changes
- TLS terminates on a raw loopback socket relayed from CONNECT. HTTP-owned detached sockets cannot be upgraded directly. The returned handshake exception is retained in session TLS metadata instead of a generic "check trust/pinning" message.
- Advertise HTTP/1.1 explicitly using ALPN. The parser does not implement HTTP/2, and does not advertise h2.
- Separate certificate-generation, client-tls-handshake, client-http, and upstream-or-http failures.
- Tunnel sessions are not marked with an error. Missing response content is displayed as not captured, not as a measured zero-byte server response.
- Keep upstream certificate validation enabled. No automatic retry without decryption, no certificate-pinning bypass, and no global certificate validation suppression.

## Validation
Automated real-socket tests cover decrypted binary bodies, all-host mode, ALPN selection, client CA rejection, untrusted upstream rejection, and unchanged encrypted tunneling. CI results must be checked before distributing a candidate APK.

**Excel/Copilot real-device HTTPS capture remains unverified.** The ALPN/handshake changes are compatibility and diagnostic improvements, not evidence that Office trust restrictions have been resolved. A trusted test client is not a substitute for Office testing.

## Device check
1. Stop capture, install the candidate, and check this installation's CA fingerprint. If an APK update requires uninstalling because signing keys differ, export needed captures first. Uninstalling loses the local CA key and requires the new CA to be installed.
2. Enable HTTPS decryption and confirm a browser captures real GET/POST requests and response bodies.
3. Reproduce Excel/Copilot separately and export HAR locally. Inspect the CONNECT session's TLS failureStage and detail. The app also displays TLS metadata in session details.
4. Check that Office and the installed CA are in the intended Android profile. An OS CA store check does not prove another app trusts that CA.
5. If client-tls-handshake fails, preserve the actual TLS error and app/Android versions for investigation. A generic alert does not prove pinning. If a released app refuses interception, an HTTP Capture change alone cannot guarantee decryption.
6. Stop capture to release the temporary VPN proxy.

Do not publish capture archives containing credentials or customer data. Logs displayed in the app remain local; export is explicit.
