"""Verify a frozen proxy against synthetic loopback HTTP and HTTPS origins.

Does not install a CA or change Windows proxy settings. Private test CA/key files
live in TemporaryDirectory only; the report contains aggregate checks.
"""
import argparse
from datetime import datetime, timedelta, timezone
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import queue
import socket
import ssl
import subprocess
import tempfile
import threading
import time

PAYLOAD = b'HTTP Capture packaged runtime\x00\xff\r\n' * 2048


class Origin(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', str(len(PAYLOAD)))
        self.send_header('X-Duplicate', 'one')
        self.send_header('X-Duplicate', 'two')
        self.end_headers()
        self.wfile.write(PAYLOAD)


def certificate(folder):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(65537, 2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
          .public_key(key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
          .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
          .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),
              x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
          .sign(key, hashes.SHA256()))
    cert, private = folder / 'origin.pem', folder / 'origin-key.pem'
    cert.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return cert, private


def smoke(engine):
    with tempfile.TemporaryDirectory(prefix='http-capture-smoke-') as directory:
        root = Path(directory)
        store = root / 'store'
        (store / 'ca').mkdir(parents=True)
        cert, key = certificate(root)
        # JSON scalar is also valid YAML; spaces and Windows backslashes are quoted.
        (store / 'ca/config.yaml').write_text('ssl_verify_upstream_trusted_ca: ' + json.dumps(str(cert)) + '\n', encoding='utf-8')
        plain = ThreadingHTTPServer(('127.0.0.1', 0), Origin)
        tls = ThreadingHTTPServer(('127.0.0.1', 0), Origin)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        tls.socket = context.wrap_socket(tls.socket, server_side=True)
        for server in (plain, tls):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        with socket.socket() as available:
            available.bind(('127.0.0.1', 0))
            port = available.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'HTTP_CAPTURE_PYTHON', 'HTTP_CAPTURE_ENGINE')}
        process = None
        try:
            process = subprocess.Popen([str(engine), '--store', str(store), '--port', str(port)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', env=env, cwd=root)
            events, pending = [], queue.Queue()
            def read():
                for line in process.stdout:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        event = {'type': 'fatal', 'error': 'Engine emitted non-JSON stdout'}
                    events.append(event)
                    pending.put(event)
                pending.put({'type': 'eof'})
            reader = threading.Thread(target=read, daemon=True)
            reader.start()
            def until(kind, timeout=45):
                end = time.monotonic() + timeout
                while time.monotonic() < end:
                    event = pending.get(timeout=max(.01, end - time.monotonic()))
                    if event['type'] in ('fatal', 'command_error', 'eof'):
                        raise RuntimeError(f'Packaged proxy failed before {kind}: {event}')
                    if event['type'] == kind:
                        return event
                raise TimeoutError(f'No {kind} event')
            until('ready')
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
            connection.request('GET', f'http://127.0.0.1:{plain.server_port}/binary')
            if connection.getresponse().read() != PAYLOAD:
                raise RuntimeError('Packaged HTTP body mismatch')
            connection.close()
            trust = ssl.create_default_context(cafile=str(store / 'ca/mitmproxy-ca-cert.pem'))
            connection = http.client.HTTPSConnection('127.0.0.1', port, context=trust, timeout=15)
            connection.set_tunnel('localhost', tls.server_port)
            connection.request('GET', '/binary')
            if connection.getresponse().read() != PAYLOAD:
                raise RuntimeError('Packaged HTTPS body mismatch')
            connection.close()
            process.stdin.write('{"id":1,"action":"stop"}\n')
            process.stdin.flush()
            until('ack')
            process.stdin.close()
            process.wait(timeout=20)
            reader.join(timeout=5)
            if process.returncode != 0:
                raise RuntimeError('Packaged engine exited unsuccessfully')
            sessions = {e['session']['id']: e['session'] for e in events if e['type'] == 'session'}
            if len(sessions) != 2:
                raise RuntimeError('Expected exactly two captured sessions')
            for session in sessions.values():
                body = session['response']['body']
                if session['captureStatus'] != 'complete' or not body['complete'] or (store / body['path']).read_bytes() != PAYLOAD:
                    raise RuntimeError('Captured body file mismatch/incomplete')
            if os.name == 'nt':
                for action in ('certificate_info', 'certificate_status'):
                    result = subprocess.run([str(engine), '--store', str(store), '--settings-action', action], input='{}\n', capture_output=True, text=True, timeout=30, env=env)
                    if result.returncode != 0 or json.loads(result.stdout.strip())['type'] != 'ack':
                        raise RuntimeError('Stopped settings failed: '+result.stdout+result.stderr)
            return {'status': 'passed', 'engine': engine.name, 'frozenRuntime': True,
                'http': 'passed', 'https': 'passed', 'binaryBytes': len(PAYLOAD), 'sessions': 2,
                'caInstalled': False, 'systemProxyModified': False}
        finally:
            if process and process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            if process:
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream:
                        stream.close()
            for server in (plain, tls):
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    result = smoke(args.engine.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
