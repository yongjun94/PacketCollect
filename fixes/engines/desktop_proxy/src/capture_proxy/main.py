import argparse
import asyncio
import contextlib
import json
import os
from pathlib import Path
import sys
import threading
from mitmproxy import certs, options
from mitmproxy.tools.dump import DumpMaster
from .config import secure_directory
from .event_writer import EventWriter
from .proxy_addon import CaptureAddon
from .windows_adapter import WindowsProxy, certificate_action


def settings_action(root, action, consent=False):
    if action == 'proxy_restore':
        return WindowsProxy(root).restore()
    if action not in ('certificate_info', 'certificate_status', 'certificate_install', 'certificate_remove'):
        raise ValueError('Unknown settings action')
    if action in ('certificate_install','certificate_remove') and consent is not True:
        raise ValueError('Explicit user consent required')
    secure_directory(root)
    secure_directory(root / 'ca')
    certs.CertStore.from_store(root / 'ca', 'mitmproxy', 2048)
    path = root / 'ca/mitmproxy-ca-cert.pem'
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    ca = x509.load_pem_x509_certificate(path.read_bytes())
    if action == 'certificate_info':
        return {'path': str(path), 'fingerprint': ca.fingerprint(hashes.SHA256()).hex().upper()}
    return certificate_action(path, action.removeprefix('certificate_'))


async def run(root, port, decrypt):
    secure_directory(root)
    secure_directory(root / 'bodies')
    secure_directory(root / 'ca')
    writer = EventWriter(root)
    certs.CertStore.from_store(root / 'ca', 'mitmproxy', 2048)
    certificate = root / 'ca' / 'mitmproxy-ca-cert.pem'
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    ca = x509.load_pem_x509_certificate(certificate.read_bytes())
    writer.emit('ca', path=str(certificate), fingerprint=ca.fingerprint(hashes.SHA256()).hex().upper())
    opts = options.Options(listen_host='127.0.0.1', listen_port=port,
                           confdir=str(root / 'ca'), http2=True)
    # Only allow an explicit private upstream trust bundle, never ssl_insecure.
    from ruamel.yaml import YAML
    config_file = root / 'ca' / 'config.yaml'
    if config_file.exists():
        settings = YAML(typ='safe').load(config_file.read_text()) or {}
        if 'ssl_verify_upstream_trusted_ca' in settings:
            opts.update(ssl_verify_upstream_trusted_ca=settings['ssl_verify_upstream_trusted_ca'])
    # HTTPS decryption disabled means CONNECT tunnels pass through unchanged.
    if not decrypt:
        opts.update(ignore_hosts=['.*'])
    master = DumpMaster(opts, with_termlog=False, with_dumper=False)
    master.options.update(connection_strategy='lazy', websocket=False)
    addon = CaptureAddon(writer)
    master.addons.add(addon)
    proxy = WindowsProxy(root)
    task = asyncio.create_task(master.run())
    # running() is invoked only after proxy listeners have been installed.
    class Ready:
        def running(self):
            writer.emit('ready', port=port, pid=os.getpid(), recoveryNeeded=proxy.journal.exists())
    master.addons.add(Ready())

    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    def reader():
        for line in sys.stdin:
            loop.call_soon_threadsafe(queue.put_nowait, line)
        loop.call_soon_threadsafe(queue.put_nowait, '')
    threading.Thread(target=reader, daemon=True).start()

    async def commands():
        while True:
            line = await queue.get()
            if not line:
                master.shutdown()
                return
            command_id = None
            try:
                cmd = json.loads(line)
                command_id = cmd.get('id')
                action = cmd['action']
                result = None
                if action == 'pause':
                    addon.paused = bool(cmd['paused'])
                elif action == 'stop':
                    master.shutdown()
                elif action == 'proxy_enable':
                    proxy.enable(port)
                elif action == 'proxy_restore':
                    result = proxy.restore()
                elif action in ('certificate_info', 'certificate_install', 'certificate_remove', 'certificate_status'):
                    if action in ('certificate_install','certificate_remove') and cmd.get('consent') is not True:
                        raise ValueError('Explicit user consent required')
                    result = settings_action(root, action, cmd.get('consent', False))
                else:
                    raise ValueError('Unknown action')
                writer.emit('ack', id=command_id, result=result)
                if action == 'stop':
                    return
            except Exception as exc:
                writer.emit('command_error', id=command_id, error=str(exc))
    control = asyncio.create_task(commands())
    try:
        await task
    finally:
        if not control.done():
            control.cancel()
        if os.name == 'nt' and proxy.journal.exists():
            try:
                proxy.restore()
            except Exception as exc:
                writer.emit('recovery_error', error=str(exc))
        writer.emit('stopped')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--store', required=True, type=Path)
    parser.add_argument('--port', type=int, default=8877)
    parser.add_argument('--no-decrypt', action='store_true')
    parser.add_argument('--recover-proxy', action='store_true')
    parser.add_argument('--settings-action')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Port must be 1024..65535')
    try:
        if args.settings_action:
            request = json.loads(sys.stdin.readline())
            result = settings_action(args.store.resolve(), args.settings_action, request.get('consent', False))
            print(json.dumps({'type':'ack','result':result}), flush=True)
            return
        if args.recover_proxy:
            result = WindowsProxy(args.store.resolve()).restore()
            print(json.dumps({'type': 'recovered', 'result': result}), flush=True)
            return
        asyncio.run(run(args.store.resolve(), args.port, not args.no_decrypt))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(json.dumps({'type': 'fatal', 'error': str(exc)}), flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
