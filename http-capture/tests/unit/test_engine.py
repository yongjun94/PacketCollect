import json
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engines/desktop_proxy/src'))
from capture_proxy.windows_adapter import WindowsProxy
from capture_proxy.event_writer import EventWriter
from capture_proxy.proxy_addon import CaptureAddon
from mitmproxy.test import tflow


def test_partial_response_closed_and_marked(tmp_path,capsys):
    (tmp_path/'bodies').mkdir()
    addon=CaptureAddon(EventWriter(tmp_path))
    flow=tflow.tflow(resp=True)
    addon.requestheaders(flow)
    flow.request.stream(b'abc')
    addon.request(flow)
    addon.responseheaders(flow)
    flow.response.stream(b'partial\x00\xff')
    addon.done()
    events=[json.loads(line) for line in capsys.readouterr().out.splitlines()]
    final=events[-1]['session']
    assert final['captureStatus']=='interrupted'
    assert final['request']['body']['complete']
    assert final['response']['body']['complete'] is False
    assert final['response']['body']['size']==9
    assert (tmp_path/final['response']['body']['path']).read_bytes()==b'partial\x00\xff'
    assert addon.active=={}


def test_pause_never_creates_body_or_session(tmp_path,capsys):
    addon=CaptureAddon(EventWriter(tmp_path));addon.paused=True
    flow=tflow.tflow(resp=True)
    addon.requestheaders(flow);addon.responseheaders(flow)
    assert flow.request.stream is True and flow.response.stream is True
    assert addon.active=={}
    assert capsys.readouterr().out==''


class FakeWindowsProxy(WindowsProxy):
    def _require(self):pass
    def read(self):return self.current
    def write(self,value):self.written=value


def test_proxy_restore_does_not_clobber_external_change(tmp_path):
    proxy=FakeWindowsProxy(tmp_path)
    before={'ProxyEnable':[0,4],'ProxyServer':None,'ProxyOverride':None}
    installed={'ProxyEnable':[1,4],'ProxyServer':['127.0.0.1:8877',1],'ProxyOverride':['<-loopback>',1]}
    proxy.journal.write_text(json.dumps({'before':before,'installed':installed}))
    proxy.current=dict(installed,ProxyServer=['corporate.example:8080',1])
    with pytest.raises(RuntimeError,match='externally'):proxy.restore()
    assert proxy.journal.exists()
    assert not hasattr(proxy,'written')
    proxy.current=installed
    assert proxy.restore()=='Proxy restored'
    assert proxy.written==before
    assert not proxy.journal.exists()
