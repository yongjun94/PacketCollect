# macOS automatic system proxy preview

Start defaults to connecting enabled network services' HTTP/HTTPS proxies after the listener is ready. macOS administrator approval may be required. Stop and normal app exit restore saved settings before closing the listener. Existing HTTP/HTTPS/SOCKS/PAC/discovery settings are refused; upstream routing is not implemented. Bypass lists remain unchanged.

A mode-0600 journal is saved before writes. External changes are not overwritten. After a crash, reopen the app to attempt recovery or use Settings > Restore / recover proxy. Immediate recovery after force kill/power loss is not guaranteed: no privileged background guardian is implemented. Denied approval or a failed restore leaves the journal for retry. Restore original network settings manually if needed.

CA trust still requires explicit user action in Keychain Access. Only import the public mitmproxy-ca-cert.pem after fingerprint verification. Never share mitmproxy-ca.pem, which includes the private key.

Scope is proxy-aware HTTP/HTTPS, not every packet. Arbitrary TCP/UDP, QUIC, bypassed hosts, apps ignoring system proxies and pinned TLS are not guaranteed. Windows also uses an HTTP proxy.

Four mocked tests pass for round-trip, existing corporate route refusal, external conflict and partial-write recovery. Real networksetup writes, authorization dialogs, browser HTTPS and crash recovery remain pending real Mac acceptance. The user's curl capture proves the prior HTTP engine path only. The app remains ad-hoc signed and not notarized.
