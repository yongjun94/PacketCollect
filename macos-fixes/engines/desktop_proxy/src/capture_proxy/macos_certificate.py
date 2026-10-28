"""User-domain SSL trust only; never imports or exposes the CA private key."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from cryptography import x509
from cryptography.hazmat.primitives import hashes


class MacCertificate:
    def __init__(self, path):
        self.path = Path(path)
        self.cert = x509.load_pem_x509_certificate(self.path.read_bytes())
        self.fingerprint = self.cert.fingerprint(hashes.SHA256()).hex().upper()
        self.thumb = self.cert.fingerprint(hashes.SHA1()).hex().upper()
        self.receipt = self.path.parent / 'macos-trust-receipt.json'

    def run(self, *args, check=True):
        result = subprocess.run(['/usr/bin/security', *args], text=True,
                                capture_output=True, timeout=180)
        if check and result.returncode:
            raise RuntimeError('macOS certificate operation failed: ' + result.stderr.strip()[-1500:])
        return result

    def keychain(self):
        paths = shlex.split(self.run('default-keychain', '-d', 'user').stdout.strip())
        if len(paths) != 1 or not Path(paths[0]).is_absolute():
            raise RuntimeError('Cannot determine the current user default keychain')
        return paths[0]

    def present(self, keychain):
        result = self.run('find-certificate', '-a', '-p', keychain, check=False)
        if result.returncode not in (0, 44):
            raise RuntimeError('Cannot inspect keychain: ' + result.stderr.strip()[-1500:])
        certs = re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', result.stdout, re.S)
        return any(x509.load_pem_x509_certificate(c.encode()).fingerprint(hashes.SHA256()).hex().upper()
                   == self.fingerprint for c in certs)

    def status(self, keychain):
        # Do not pass -r: explicitly supplying a root would falsely establish trust.
        result = self.run('verify-cert', '-c', str(self.path), '-p', 'ssl', '-l', '-L', check=False)
        return dict(fingerprint=self.fingerprint, trusted=result.returncode == 0,
                    present=self.present(keychain), keychain=keychain,
                    managed=self.receipt.exists(), scope='current-user SSL',
                    detail=(result.stderr or result.stdout).strip()[-1500:])

    def action(self, action, consent=False):
        if sys.platform != 'darwin':
            raise RuntimeError('macOS only')
        if action not in ('status', 'install', 'remove'):
            raise ValueError('Unknown certificate action')
        if action != 'status' and consent is not True:
            raise ValueError('Explicit user consent required')
        keychain = self.keychain()
        if action == 'status':
            return self.status(keychain)
        receipt = json.loads(self.receipt.read_text()) if self.receipt.exists() else None
        if receipt and (receipt.get('fingerprint') != self.fingerprint or receipt.get('keychain') != keychain):
            raise RuntimeError('CA ownership/keychain changed; inspect Keychain Access manually')
        present = self.present(keychain)
        if action == 'install':
            if present and not receipt:
                if self.status(keychain)['trusted']:
                    return self.status(keychain)
                raise RuntimeError('This CA already exists outside app management. Configure its SSL trust in Keychain Access; it will not be overwritten.')
            if not receipt:
                with self.receipt.open('x') as out:
                    os.chmod(self.receipt, 0o600)
                    json.dump(dict(fingerprint=self.fingerprint, keychain=keychain), out)
                    out.flush()
                    os.fsync(out.fileno())
            self.run('add-trusted-cert', '-r', 'trustRoot', '-p', 'ssl', '-k', keychain, str(self.path))
            status = self.status(keychain)
            if not status['trusted']:
                raise RuntimeError('CA added but SSL trust verification failed. Check macOS approval or managed policy in Keychain Access.')
            return status
        if not receipt:
            raise RuntimeError('No app installation receipt; refusing to delete an unmanaged certificate')
        if present:
            # SHA-256 was matched against the actual keychain certificate above.
            # security uses SHA-1 as the deletion identifier, never the generic CA name.
            self.run('delete-certificate', '-Z', self.thumb, '-t', keychain)
        else:
            self.run('remove-trusted-cert', str(self.path))
        if self.present(keychain):
            raise RuntimeError('Certificate removal verification failed')
        self.receipt.unlink()
        return self.status(keychain)
