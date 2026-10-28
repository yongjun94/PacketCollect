# macOS CA trust

Settings now provides explicit-consent CA install/SSL trust, status and remove actions. Start with HTTPS decryption checks SSL trust first and offers installation before applying the system proxy. Only the public certificate is added to the current user default keychain. security add-trusted-cert uses user-domain SSL policy, never global trust or the private key. macOS authorization is not bypassed.

Status uses security verify-cert with SSL policy, local-only chain lookup, and CA-leaf allowance. It never supplies a root via -r (which would falsely create trust for the check). Trust verification does not guarantee every browser/app accepts the CA; pinning and managed policies still apply.

A mode-0600 receipt records this installation's SHA-256 and target keychain before mutation. Removal requires that receipt and matches the actual keychain certificate by SHA-256 before using security's SHA-1 deletion identifier. Unmanaged pre-existing certificates are not changed/deleted; use Keychain Access manually if one was imported earlier. Failed or canceled authorization is shown as an error, not success. CA/private key files remain local after removing OS trust so captured data is not affected.

Five mock tests cover consent, install/status/remove, existing unmanaged certificates, denied approval and fingerprint mismatch. Real macOS authorization UI, Keychain Access state and Safari HTTPS acceptance remain manual checks. After installing, reopen Safari and retry. Do not bypass browser certificate warnings for unrelated certificates.
