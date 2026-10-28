"""Conservative networksetup adapter. Never changes CA trust or PAC settings."""
import json
import os
import shlex
import subprocess
import sys

NETWORKSETUP = '/usr/sbin/networksetup'


class MacProxy:
    def __init__(self, root):
        self.journal = root / 'proxy-journal.json'

    def read(self, *args):
        env = dict(os.environ, LC_ALL='C', LANG='C')
        return subprocess.run([NETWORKSETUP, *args], env=env, text=True,
                              capture_output=True, check=True, timeout=15).stdout.strip()

    def state(self, service, kind):
        lines = self.read('-get' + kind, service).splitlines()
        fields = dict(line.split(': ', 1) for line in lines if ': ' in line)
        if fields.get('Enabled') not in ('Yes', 'No'):
            raise RuntimeError('Cannot read proxy settings for ' + service)
        return fields

    def write(self, commands):
        if not commands:
            return
        # All tokens are shell quoted; AppleScript string is separately JSON escaped.
        script = 'set -e\n' + '\n'.join(shlex.join([NETWORKSETUP, *cmd]) for cmd in commands)
        result = subprocess.run(['/usr/bin/osascript', '-e',
                                 'do shell script ' + json.dumps(script) + ' with administrator privileges'],
                                text=True, capture_output=True, timeout=180)
        if result.returncode:
            raise RuntimeError('macOS proxy authorization/apply failed: ' + result.stderr.strip())

    def enable(self, port):
        if sys.platform != 'darwin':
            raise RuntimeError('macOS only')
        if self.journal.exists():
            raise RuntimeError('Recover previous proxy settings before starting')
        services = [s for s in self.read('-listallnetworkservices').splitlines()[1:]
                    if s and not s.startswith('*')]
        records = []
        for service in services:
            # Fail closed for existing corporate routes, even disabled authenticated endpoints.
            for kind in ('webproxy', 'securewebproxy', 'socksfirewallproxy', 'autoproxyurl'):
                state = self.state(service, kind)
                if state['Enabled'] == 'Yes' or state.get('Authenticated Proxy Enabled') == '1':
                    raise RuntimeError('Existing proxy/PAC on ' + service + '; upstream routing is not supported')
            if self.read('-getproxyautodiscovery', service).split(':')[-1].strip().lower() != 'off':
                raise RuntimeError('Automatic proxy discovery on ' + service + '; refusing takeover')
            for kind in ('webproxy', 'securewebproxy'):
                before = self.state(service, kind)
                records.append(dict(service=service, kind=kind, before=before, port=str(port)))
        if not records:
            raise RuntimeError('No enabled network services')
        self.journal.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.journal.open('x', encoding='utf-8') as out:
            os.chmod(self.journal, 0o600)
            json.dump(records, out)
            out.flush()
            os.fsync(out.fileno())
        commands = []
        for record in records:
            commands += [('-set' + record['kind'], record['service'], '127.0.0.1', str(port)),
                         ('-set' + record['kind'] + 'state', record['service'], 'on')]
        self.write(commands)
        for record in records:
            current = self.state(record['service'], record['kind'])
            if not self.owned(current, record):
                raise RuntimeError('Proxy settings did not apply; recover before retrying')

    @staticmethod
    def owned(current, record):
        return (current.get('Enabled') == 'Yes' and current.get('Server') == '127.0.0.1'
                and current.get('Port') == record['port']
                and current.get('Authenticated Proxy Enabled', '0') == '0')

    def restore(self):
        if not self.journal.exists():
            return 'No recovery needed'
        records = json.loads(self.journal.read_text())
        commands = []
        for record in records:
            service, kind, before = record['service'], record['kind'], record['before']
            current = self.state(service, kind)
            if current == before:
                continue
            # The endpoint may be written but not yet enabled after a partial failure.
            partial = dict(current, Enabled='Yes')
            if not self.owned(partial, record):
                raise RuntimeError('Proxy changed externally on ' + service + '; manual recovery required')
            server, port = before.get('Server', ''), before.get('Port', '0')
            commands.append(('-set' + kind + 'state', service, 'off'))
            commands.append(('-set' + kind, service, server, port))
            commands.append(('-set' + kind + 'state', service, 'off'))
        self.write(commands)
        for record in records:
            if self.state(record['service'], record['kind']) != record['before']:
                raise RuntimeError('Restore verification failed; journal retained')
        self.journal.unlink()
        return 'Proxy settings restored'
