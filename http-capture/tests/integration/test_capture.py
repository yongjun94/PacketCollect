"""Real loopback upstream + mitmproxy + Dart store/export; no external traffic."""
import base64
import gzip
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import socket
import ssl
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[2]
RAW = bytes(range(256)) * 4096
GZIP = gzip.compress(RAW, mtime=0)


class Origin(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *args):
        pass
    def do_GET(self):
        if self.path == '/chunked':
            self.send_response(200)
            self.send_header('Transfer-Encoding', 'chunked')
            self.send_header('Content-Type', 'application/octet-stream')
            self.end_headers()
            for chunk in (b'abc', b'\x00\xff\r\n'):
                self.wfile.write(f'{len(chunk):x}\r\n'.encode() + chunk + b'\r\n')
            self.wfile.write(b'0\r\n\r\n')
            return
        data = GZIP if self.path == '/gzip' else RAW
        self.send_response(302 if self.path == '/redirect' else 200)
        if self.path == '/redirect':
            self.send_header('Location', '/binary')
        if self.path == '/gzip':
            self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Set-Cookie', 'a=1; HttpOnly; Path=/')
        self.send_header('Set-Cookie', 'b=2; Secure')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        self.send_response(200)
        self.send_header('Content-Type', self.headers.get('Content-Type', 'application/octet-stream'))
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def server_certificate(tmp):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from datetime import datetime, timedelta, timezone
    import ipaddress
    key = rsa.generate_private_key(65537, 2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    cert = x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc)-timedelta(days=1)).not_valid_after(datetime.now(timezone.utc)+timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False).sign(key, hashes.SHA256())
    certpath, keypath = tmp/'server.pem', tmp/'server-key.pem'
    certpath.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keypath.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return certpath, keypath


def test_end_to_end(tmp_path):
    plain = ThreadingHTTPServer(('127.0.0.1', 0), Origin)
    tls = ThreadingHTTPServer(('127.0.0.1', 0), Origin)
    cert, key = server_certificate(tmp_path)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    tls.socket = ctx.wrap_socket(tls.socket, server_side=True)
    for server in (plain, tls):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    store = tmp_path/'capture'
    proxy_port = free_port()
    env = dict(os.environ, PYTHONPATH=str(ROOT/'engines/desktop_proxy/src'))
    # Trust the local upstream only for this test via SSL_CERT_FILE does not affect mitmproxy.
    # Use an explicit test-only mitmproxy config; production never sets ssl_insecure.
    (store/'ca').mkdir(parents=True)
    (store/'ca/config.yaml').write_text(f'ssl_verify_upstream_trusted_ca: {cert}\n')
    p = subprocess.Popen([sys.executable, '-m', 'capture_proxy.main', '--store', str(store), '--port', str(proxy_port)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    events = []
    q = queue.Queue()
    def reader():
        for line in p.stdout:
            e = json.loads(line)
            events.append(e)
            q.put(e)
    threading.Thread(target=reader, daemon=True).start()
    def until(kind, timeout=20):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            e = q.get(timeout=max(.01, deadline-time.monotonic()))
            if e['type']=='fatal':
                pytest.fail(e['error'])
            if e['type']==kind:
                return e
        pytest.fail(f'No {kind}')
    def command(action, **data):
        p.stdin.write(json.dumps({'action': action, **data})+'\n'); p.stdin.flush()
        return until('ack')
    expected = []
    try:
        until('ready')
        for path, body in [('/binary',RAW),('/gzip',GZIP),('/chunked',b'abc\x00\xff\r\n'),('/redirect',RAW)]:
            conn = http.client.HTTPConnection('127.0.0.1',proxy_port,timeout=10)
            conn.request('GET',f'http://127.0.0.1:{plain.server_port}{path}',headers={'Cookie':'a=1; b=2','Authorization':'Bearer local-fixture'})
            response=conn.getresponse()
            assert response.read()==body
            conn.close()
            expected.append(body)
        tls_context = ssl.create_default_context(cafile=str(store/'ca/mitmproxy-ca-cert.pem'))
        conn = http.client.HTTPSConnection('127.0.0.1',proxy_port,context=tls_context,timeout=10)
        conn.set_tunnel('localhost',tls.server_port)
        conn.request('POST','/echo',b'{"test":true}',{'Content-Type':'application/json'})
        assert conn.getresponse().read()==b'{"test":true}'
        conn.close()
        expected.append(b'{"test":true}')
        for method in ('PUT','PATCH','DELETE'):
            conn=http.client.HTTPConnection('127.0.0.1',proxy_port,timeout=10)
            conn.request(method,f'http://127.0.0.1:{plain.server_port}/echo',b'a=1&b=2',{'Content-Type':'application/x-www-form-urlencoded'})
            assert conn.getresponse().read()==b'a=1&b=2'
            expected.append(b'a=1&b=2');conn.close()
        command('pause',paused=True)
        conn=http.client.HTTPConnection('127.0.0.1',proxy_port,timeout=10)
        conn.request('GET',f'http://127.0.0.1:{plain.server_port}/paused')
        assert conn.getresponse().read()==RAW
        conn.close()
        command('pause',paused=False)
        conn=http.client.HTTPConnection('127.0.0.1',proxy_port,timeout=10)
        conn.request('GET',f'http://127.0.0.1:{free_port()}/refused')
        conn.getresponse().read();conn.close()
        command('stop')
        p.wait(timeout=20)
        assert p.returncode==0, p.stderr.read()
    finally:
        if p.poll() is None:
            p.kill();p.wait()
        for server in (plain,tls):
            server.shutdown();server.server_close()
    final = {e['session']['id']:e['session'] for e in events if e['type']=='session'}
    assert len(final)==9
    complete = [s for s in final.values() if s['captureStatus']=='complete']
    assert len(complete)==8
    assert any(s['captureStatus']=='error' for s in final.values())
    for s, body in zip(complete,expected):
        ref=s['response']['body']
        assert ref['complete']
        assert (store/ref['path']).read_bytes()==body
    assert not any('/paused' in s['request']['url'] for s in final.values())
    (store/'events.ndjson').write_text('\n'.join(json.dumps(e) for e in events)+'\n')
    dart = os.environ.get('DART','dart')
    output = tmp_path/'export'
    result = subprocess.run([dart,'run','bin/export_capture.dart',str(store),str(output)],cwd=ROOT/'packages/capture_export',capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    har=json.loads(output.with_suffix('.har').read_text())
    assert len(har['log']['entries'])==9
    with zipfile.ZipFile(output.with_suffix('.saz')) as z:
        assert z.testzip() is None
        assert '[Content_Types].xml' in z.namelist()
        ET.fromstring(z.read('[Content_Types].xml'))
        for i,s in enumerate(final.values(),1):
            ET.fromstring(z.read(f'raw/{i}_m.xml'))
            req=z.read(f'raw/{i}_c.txt')
            assert b'\r\n\r\n' in req
            if s['response'] is not None:
                response=z.read(f'raw/{i}_s.txt')
                body=response.split(b'\r\n\r\n',1)[1]
                assert body==(store/s['response']['body']['path']).read_bytes()
                assert b'Transfer-Encoding:' not in response.split(b'\r\n\r\n',1)[0]
    # Retain only synthetic fixtures, never CA private keys or live captured traffic.
    if dest := os.environ.get('CAPTURE_ARTIFACTS'):
        import shutil
        dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
        for suffix in ('.har','.saz'):
            shutil.copyfile(output.with_suffix(suffix),dest/f'loopback{suffix}')
        (dest/'integration-summary.json').write_text(json.dumps({'sessions':len(final),'complete':len(complete),'error':1,'binarySha256':hashlib.sha256(RAW).hexdigest()},indent=2))
