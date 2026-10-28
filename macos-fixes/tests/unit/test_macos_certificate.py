import datetime
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

spec = importlib.util.spec_from_file_location('macos_certificate', Path(__file__).resolve().parents[2] / 'engines/desktop_proxy/src/capture_proxy/macos_certificate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Fake(module.MacCertificate):
    def __init__(self, path):
        super().__init__(path)
        self.installed = False
        self.trusted = False
        self.calls = []
        self.fail_install = False

    def run(self, *args, check=True):
        self.calls.append(args)
        code, output = 0, ''
        if args[0] == 'default-keychain':
            output = '"/Users/test/Library/Keychains/login.keychain-db"'
        if args[0] == 'find-certificate':
            output = self.path.read_text() if self.installed else ''
        if args[0] == 'verify-cert':
            code = 0 if self.trusted else 1
        if args[0] == 'add-trusted-cert':
            if self.fail_install:
                raise RuntimeError('User denied authorization')
            self.installed = self.trusted = True
        if args[0] == 'delete-certificate':
            self.installed = self.trusted = False
        return subprocess.CompletedProcess(args, code, output, '')


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.platform = patch.object(module.sys, 'platform', 'darwin')
        self.platform.start()
        self.addCleanup(self.platform.stop)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Fixture only')])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=1))
                .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                .sign(key, hashes.SHA256()))
        path = Path(self.temp.name) / 'public-ca.pem'
        path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        self.ca = Fake(path)

    def test_install_verify_and_exact_remove(self):
        self.assertTrue(self.ca.action('install', True)['trusted'])
        self.assertTrue(self.ca.receipt.exists())
        self.assertFalse(self.ca.action('remove', True)['trusted'])
        self.assertFalse(self.ca.receipt.exists())
        add = next(c for c in self.ca.calls if c[0] == 'add-trusted-cert')
        self.assertNotIn('-d', add)
        self.assertIn('ssl', add)
        delete = next(c for c in self.ca.calls if c[0] == 'delete-certificate')
        self.assertEqual(delete[2], self.ca.thumb)
        verify = next(c for c in self.ca.calls if c[0] == 'verify-cert')
        self.assertNotIn('-r', verify)
        self.assertIn('-l', verify)
        self.assertIn('-L', verify)

    def test_explicit_consent_required(self):
        for action in ('install', 'remove'):
            with self.assertRaises(ValueError):
                self.ca.action(action)
        self.assertFalse(self.ca.calls)

    def test_unmanaged_existing_certificate_unchanged(self):
        self.ca.installed = True
        for action in ('install', 'remove'):
            with self.assertRaises(RuntimeError):
                self.ca.action(action, True)
        self.assertFalse(any(c[0] in ('add-trusted-cert', 'delete-certificate') for c in self.ca.calls))

    def test_denied_approval_is_not_success(self):
        self.ca.fail_install = True
        with self.assertRaisesRegex(RuntimeError, 'denied'):
            self.ca.action('install', True)
        self.assertFalse(self.ca.action('status')['trusted'])

    def test_receipt_fingerprint_mismatch_refuses_delete(self):
        self.ca.action('install', True)
        self.ca.receipt.write_text('{"fingerprint":"wrong","keychain":"wrong"}')
        with self.assertRaises(RuntimeError):
            self.ca.action('remove', True)
        self.assertTrue(self.ca.installed)


if __name__ == '__main__':
    unittest.main()
