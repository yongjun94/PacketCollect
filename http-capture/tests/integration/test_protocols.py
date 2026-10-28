import asyncio
import base64
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
import pytest
from test_capture import ROOT, free_port, server_certificate


def launch(tmp_path, extra=()):
    store=tmp_path/'capture';port=free_port()
    p=subprocess.Popen([sys.executable,'-m','capture_proxy.main','--store',str(store),'--port',str(port),*extra],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=dict(os.environ,PYTHONPATH=str(ROOT/'engines/desktop_proxy/src')))
    events=[];q=queue.Queue()
    def reader():
        for line in p.stdout:
            e=json.loads(line);events.append(e);q.put(e)
    threading.Thread(target=reader,daemon=True).start()
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        e=q.get(timeout=15)
        if e['type']=='fatal':
            p.kill();pytest.fail(e['error'])
        if e['type']=='ready':break
    return p,store,port,events


def stop(p):
    if p.poll() is None:
        p.stdin.write('{"action":"stop"}\n');p.stdin.flush();p.wait(timeout=15)
    assert p.returncode==0,p.stderr.read()


def test_http2_tls_and_duplicate_headers(tmp_path):
    import h2.config
    import h2.connection
    import h2.events
    cert,key=server_certificate(tmp_path)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
    upstream_port=listener.getsockname()[1]
    server_ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);server_ctx.load_cert_chain(cert,key);server_ctx.set_alpn_protocols(['h2'])
    errors=[]
    def origin():
        try:
            raw,_=listener.accept()
            with server_ctx.wrap_socket(raw,server_side=True) as s:
                s.settimeout(10)
                assert s.selected_alpn_protocol()=='h2'
                h=h2.connection.H2Connection(config=h2.config.H2Configuration(client_side=False))
                h.initiate_connection();s.sendall(h.data_to_send())
                while True:
                    data=s.recv(65536)
                    if not data:break
                    for e in h.receive_data(data):
                        if isinstance(e,h2.events.StreamEnded):
                            h.send_headers(e.stream_id,[(b':status',b'200'),(b'content-type',b'application/octet-stream'),(b'x-duplicate',b'one'),(b'x-duplicate',b'two')])
                            h.send_data(e.stream_id,b'http2\x00\xff',end_stream=True)
                    s.sendall(h.data_to_send())
        except Exception as exc:errors.append(str(exc))
    threading.Thread(target=origin,daemon=True).start()
    store=tmp_path/'capture';(store/'ca').mkdir(parents=True)
    (store/'ca/config.yaml').write_text(f'ssl_verify_upstream_trusted_ca: {cert}\n')
    p,store,port,events=launch(tmp_path)
    try:
        raw=socket.create_connection(('127.0.0.1',port),timeout=10)
        raw.sendall(f'CONNECT localhost:{upstream_port} HTTP/1.1\r\nHost: localhost:{upstream_port}\r\n\r\n'.encode())
        response=b''
        while b'\r\n\r\n' not in response:response+=raw.recv(1)
        assert b'200' in response
        ctx=ssl.create_default_context(cafile=str(store/'ca/mitmproxy-ca-cert.pem'));ctx.set_alpn_protocols(['h2'])
        with ctx.wrap_socket(raw,server_hostname='localhost') as s:
            assert s.selected_alpn_protocol()=='h2'
            h=h2.connection.H2Connection();h.initiate_connection()
            h.send_headers(1,[(':method','GET'),(':scheme','https'),(':authority',f'localhost:{upstream_port}'),(':path','/h2')],end_stream=True)
            s.sendall(h.data_to_send());body=b'';done=False
            while not done:
                for e in h.receive_data(s.recv(65536)):
                    if isinstance(e,h2.events.DataReceived):body+=e.data;h.acknowledge_received_data(e.flow_controlled_length,e.stream_id)
                    if isinstance(e,h2.events.StreamEnded):done=True
                s.sendall(h.data_to_send())
            assert body==b'http2\x00\xff'
        stop(p)
        terminal=[e['session'] for e in events if e['type']=='session' and e['session']['captureStatus']=='complete']
        assert len(terminal)==1
        s=terminal[0]
        assert s['request']['version']=='HTTP/2.0'
        dup=[base64.b64decode(h['value']) for h in s['response']['headers'] if base64.b64decode(h['name'])==b'x-duplicate']
        assert dup==[b'one',b'two']
        assert (store/s['response']['body']['path']).read_bytes()==b'http2\x00\xff'
        assert not errors
    finally:
        if p.poll() is None:p.kill();p.wait()
        listener.close()


def test_no_decrypt_tunnel_and_ca_uniqueness(tmp_path):
    from http.server import ThreadingHTTPServer
    from test_capture import Origin, RAW
    import http.client
    cert,key=server_certificate(tmp_path)
    server=ThreadingHTTPServer(('127.0.0.1',0),Origin)
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cert,key)
    server.socket=ctx.wrap_socket(server.socket,server_side=True)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    p,store,port,events=launch(tmp_path,('--no-decrypt',))
    try:
        client=http.client.HTTPSConnection('127.0.0.1',port,context=ssl.create_default_context(cafile=str(cert)),timeout=10)
        client.set_tunnel('localhost',server.server_port);client.request('GET','/binary')
        assert client.getresponse().read()==RAW;client.close();stop(p)
        assert not [e for e in events if e['type']=='session']
        first=next(e['fingerprint'] for e in events if e['type']=='ca')
        second_root=tmp_path/'other'
        p2,_,_,events2=launch(second_root);stop(p2)
        assert first!=next(e['fingerprint'] for e in events2 if e['type']=='ca')
    finally:
        if p.poll() is None:p.kill();p.wait()
        server.shutdown();server.server_close()


def test_bind_failure_exits_without_waiting_for_stdin(tmp_path):
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));s.listen()
        p=subprocess.Popen([sys.executable,'-m','capture_proxy.main','--store',str(tmp_path/'capture'),'--port',str(s.getsockname()[1])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=dict(os.environ,PYTHONPATH=str(ROOT/'engines/desktop_proxy/src')))
        try:
            assert p.wait(timeout=10)!=0
        finally:
            if p.poll() is None:p.kill();p.wait()
