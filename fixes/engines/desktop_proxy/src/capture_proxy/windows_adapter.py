"""Current-user WinINet only. Compare-before-restore journal, never WinHTTP."""
import ctypes
import json
import os
from pathlib import Path
import subprocess

KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
NAMES = ("ProxyEnable", "ProxyServer", "ProxyOverride")


def validate_proxy_takeover(before):
    """Refuse to replace a configured PAC or an active explicit proxy.

    This is not a PAC/WPAD resolver. The adapter does not chain an existing
    proxy and must not imply that enterprise routing is preserved.
    """
    pac = before.get('AutoConfigURL')
    if pac is not None and (not isinstance(pac, (list, tuple)) or len(pac) != 2):
        raise RuntimeError('Cannot safely determine PAC configuration; system proxy not changed.')
    if pac is not None and str(pac[0]).strip():
        raise RuntimeError('PAC proxy detected. System proxy not changed; PAC upstream chaining is not implemented.')
    enabled = before.get('ProxyEnable')
    if enabled is not None:
        if not isinstance(enabled, (list, tuple)) or len(enabled) != 2 or not isinstance(enabled[0], int):
            raise RuntimeError('Cannot safely determine existing proxy state; system proxy not changed.')
        if enabled[0] != 0:
            raise RuntimeError('An existing system proxy is active. Automatic takeover is unavailable because upstream chaining is not implemented; system proxy not changed.')


class WindowsProxy:
    def __init__(self, root: Path):
        self.journal = root / "proxy-journal.json"

    def _require(self):
        if os.name != 'nt':
            raise RuntimeError('System proxy adapter is implemented for Windows only')

    def read(self):
        self._require()
        import winreg
        values = {}
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            for name in (*NAMES, 'AutoConfigURL'):
                try:
                    value, kind = winreg.QueryValueEx(key, name)
                    values[name] = [value, kind]
                except FileNotFoundError:
                    values[name] = None
        return values

    def write(self, values):
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as key:
            for name in NAMES:
                val = values[name]
                if val is None:
                    try:
                        winreg.DeleteValue(key, name)
                    except FileNotFoundError:
                        pass
                else:
                    winreg.SetValueEx(key, name, 0, val[1], val[0])
        from ctypes import wintypes
        wininet = ctypes.WinDLL('wininet', use_last_error=True)
        notify = wininet.InternetSetOptionW
        notify.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD]
        notify.restype = wintypes.BOOL
        for option in (39, 37):
            if not notify(None, option, None, 0):
                raise ctypes.WinError(ctypes.get_last_error())

    def enable(self, port):
        self._require()
        import winreg
        if self.journal.exists():
            raise RuntimeError('Unresolved proxy journal. Recover before starting.')
        before = self.read()
        # Static proxy and PAC are not forwarded by this engine; do not replace them.
        # WPAD and VPN-specific connection options are not checked here.
        validate_proxy_takeover(before)
        installed = dict(before, ProxyEnable=[1, winreg.REG_DWORD],
                         ProxyServer=[f'127.0.0.1:{port}', winreg.REG_SZ],
                         ProxyOverride=['<-loopback>', winreg.REG_SZ])
        with open(self.journal, 'x') as f:
            json.dump({'before': before, 'installed': installed}, f)
            f.flush()
            os.fsync(f.fileno())
        try:
            self.write(installed)
        except Exception:
            self.restore()
            raise

    def restore(self):
        self._require()
        if not self.journal.exists():
            return 'No recovery required'
        state = json.loads(self.journal.read_text())
        current = self.read()
        # Accept a partly applied tuple, but refuse another actor's values.
        if (current.get('AutoConfigURL') != state['before'].get('AutoConfigURL') or
                any(current[n] not in (state['before'][n], state['installed'][n]) for n in NAMES)):
            raise RuntimeError('Proxy changed externally. Journal kept; manual review required.')
        self.write(state['before'])
        self.journal.unlink()
        return 'Proxy restored'


def certificate_action(cert_path, action):
    if os.name != 'nt':
        raise RuntimeError('Certificate trust adapter is implemented for Windows only')
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    cert = x509.load_pem_x509_certificate(Path(cert_path).read_bytes())
    thumb = cert.fingerprint(hashes.SHA1()).hex().upper()
    fingerprint = cert.fingerprint(hashes.SHA256()).hex().upper()
    import base64
    from cryptography.hazmat.primitives.serialization import Encoding
    script = r"""
$j = [Console]::In.ReadToEnd() | ConvertFrom-Json
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
$cert.Import([Convert]::FromBase64String($j.der))
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store('Root','CurrentUser')
try {
 $mode = [System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly
 if ($j.action -ne 'status') { $mode = [System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite }
 $store.Open($mode)
 $matches = $store.Certificates.Find([System.Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint,$j.thumb,$false)
 foreach ($c in $matches) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $fp = [BitConverter]::ToString($sha.ComputeHash($c.RawData)).Replace('-','')
  if ($fp -ne $j.fingerprint) { throw 'Certificate fingerprint mismatch' }
 }
 if ($j.action -eq 'install') { $store.Add($cert) }
 if ($j.action -eq 'remove') { foreach ($c in $matches) { $store.Remove($c) } }
 $present = $store.Certificates.Find([System.Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint,$j.thumb,$false).Count -gt 0
 $present | ConvertTo-Json -Compress
} finally { $store.Close(); $cert.Dispose() }
"""
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                            "$ErrorActionPreference='Stop';" + script],
                            input=json.dumps({'thumb': thumb, 'fingerprint': fingerprint,
                                'action': action, 'der': base64.b64encode(cert.public_bytes(Encoding.DER)).decode('ascii')}),
                            text=True, capture_output=True, timeout=20, errors='replace')
    if result.returncode != 0:
        raise RuntimeError('Certificate ' + action + ' failed: ' + result.stderr.strip()[-1500:])
    return {'fingerprint': fingerprint, 'trusted': json.loads(result.stdout.strip())}

