"""Safety decisions run on any OS without touching actual network settings."""
import sys
import json
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engines' / 'desktop_proxy' / 'src'))
from capture_proxy.windows_adapter import WindowsProxy, validate_proxy_takeover


class ProxyTakeoverSafetyTests(unittest.TestCase):
    def test_active_proxy_and_pac_are_rejected(self):
        for state in (
            {'ProxyEnable': [1, 4], 'ProxyServer': ['company:8080', 1], 'AutoConfigURL': None},
            {'ProxyEnable': [0, 4], 'AutoConfigURL': ['https://company/pac', 1]},
            {'ProxyEnable': ['unknown', 1], 'AutoConfigURL': None},
            {'ProxyEnable': [0, 4], 'AutoConfigURL': ['missing-type']},
        ):
            with self.subTest(state=state), self.assertRaises(RuntimeError):
                validate_proxy_takeover(state)
        validate_proxy_takeover({'ProxyEnable': [0, 4], 'AutoConfigURL': None})
        validate_proxy_takeover({'ProxyEnable': [0, 4], 'AutoConfigURL': ['', 1]})

    def test_restore_refuses_to_overwrite_when_pac_changed_externally(self):
        with TemporaryDirectory() as root:
            proxy = WindowsProxy(Path(root))
            proxy._require = lambda: None
            before = {'ProxyEnable': [0, 4], 'ProxyServer': None, 'ProxyOverride': None, 'AutoConfigURL': None}
            installed = dict(before, ProxyEnable=[1, 4], ProxyServer=['127.0.0.1:8877', 1], ProxyOverride=['<-loopback>', 1])
            proxy.journal.write_text(json.dumps({'before': before, 'installed': installed}))
            proxy.read = lambda: dict(installed, AutoConfigURL=['https://company/pac', 1])
            proxy.write = lambda value: self.fail('External PAC change must not be overwritten')
            with self.assertRaisesRegex(RuntimeError, 'externally'):
                proxy.restore()
            self.assertTrue(proxy.journal.exists())

    def test_rejected_takeover_creates_no_journal_and_makes_no_writes(self):
        with TemporaryDirectory() as root:
            proxy = WindowsProxy(Path(root))
            proxy._require = lambda: None
            proxy.read = lambda: {'ProxyEnable': [1, 4], 'ProxyServer': ['company:8080', 1], 'AutoConfigURL': None}
            proxy.write = lambda value: self.fail('An existing proxy must not be modified')
            fake_winreg = types.SimpleNamespace(REG_DWORD=4, REG_SZ=1)
            with patch.dict(sys.modules, {'winreg': fake_winreg}):
                with self.assertRaisesRegex(RuntimeError, 'existing system proxy'):
                    proxy.enable(8877)
            self.assertFalse(proxy.journal.exists())


if __name__ == '__main__':
    unittest.main()
