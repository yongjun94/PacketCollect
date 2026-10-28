import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('macos_adapter', Path(__file__).resolve().parents[2] / 'engines/desktop_proxy/src/capture_proxy/macos_adapter.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Fake(module.MacProxy):
    def __init__(self, root):
        super().__init__(root)
        self.states = {k: dict(Enabled='No', Server='', Port='0', **{'Authenticated Proxy Enabled': '0'}) for k in ('webproxy', 'securewebproxy', 'socksfirewallproxy', 'autoproxyurl')}
        self.calls = []
        self.discovery = 'Auto Proxy Discovery: Off'

    def read(self, *args):
        return 'An asterisk denotes disabled services.\nWi-Fi' if args[0] == '-listallnetworkservices' else self.discovery

    def state(self, service, kind):
        return self.states[kind].copy()

    def write(self, commands):
        self.calls.extend(commands)
        for action, service, *values in commands:
            if action.endswith('state'):
                self.states[action[4:-5]]['Enabled'] = 'Yes' if values[0] == 'on' else 'No'
            else:
                self.states[action[4:]].update(Server=values[0], Port=values[1], Enabled='Yes')


class Tests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module.sys, 'platform', 'darwin'):
            proxy = Fake(Path(directory))
            original = {k: v.copy() for k, v in proxy.states.items()}
            proxy.enable(8877)
            self.assertTrue(proxy.journal.exists())
            self.assertEqual(proxy.states['securewebproxy']['Port'], '8877')
            proxy.restore()
            self.assertEqual(proxy.states, original)
            self.assertFalse(proxy.journal.exists())

    def test_pac_and_discovery_rejected_without_mutation(self):
        for kind in ('webproxy', 'securewebproxy', 'socksfirewallproxy', 'autoproxyurl', 'discovery'):
            with tempfile.TemporaryDirectory() as directory, patch.object(module.sys, 'platform', 'darwin'):
                proxy = Fake(Path(directory))
                if kind == 'discovery':
                    proxy.discovery = 'Auto Proxy Discovery: On'
                else:
                    proxy.states[kind]['Enabled'] = 'Yes'
                with self.assertRaises(RuntimeError):
                    proxy.enable(8877)
                self.assertFalse(proxy.journal.exists())
                self.assertFalse(proxy.calls)

    def test_external_change_retains_journal(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module.sys, 'platform', 'darwin'):
            proxy = Fake(Path(directory))
            proxy.enable(8877)
            proxy.states['webproxy']['Server'] = 'corporate.example'
            proxy.calls.clear()
            with self.assertRaises(RuntimeError):
                proxy.restore()
            self.assertTrue(proxy.journal.exists())
            self.assertFalse(proxy.calls)

    def test_partial_write_restores(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module.sys, 'platform', 'darwin'):
            proxy = Fake(Path(directory))
            proxy.enable(8877)
            proxy.states['webproxy']['Enabled'] = 'No'
            proxy.restore()
            self.assertFalse(proxy.journal.exists())


if __name__ == '__main__':
    unittest.main()
