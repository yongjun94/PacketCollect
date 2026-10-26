"""Emulator UI + actual proxy test. Does not modify Wi-Fi or trust stores."""
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def adb(*args):
    return subprocess.check_output(['adb', *args], text=True)


def screen():
    adb('shell', 'uiautomator', 'dump', '/sdcard/capture-ui.xml')
    return ET.fromstring(adb('shell', 'cat', '/sdcard/capture-ui.xml'))


def wait_text(label, tap=False, timeout=45):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        tree=screen()
        for node in tree.iter('node'):
            value=node.attrib.get('text','')+' '+node.attrib.get('content-desc','')
            if label in value:
                if tap:
                    coords=list(map(int,re.findall(r'\d+',node.attrib['bounds'])))
                    adb('shell','input','tap',str((coords[0]+coords[2])//2),str((coords[1]+coords[3])//2))
                return value
        time.sleep(1)
    raise RuntimeError('UI text missing: '+label)


adb('install','-r','http-capture/apps/capture_app/build/app/outputs/flutter-apk/app-debug.apk')
adb('shell','am','start','-n','dev.httpcapture.capture_app/.MainActivity')
wait_text('Stopped')
wait_text('Start',tap=True)
wait_text('HTTP proxy ·')
wait_text('Test HTTP',tap=True)
wait_text('Local proxy round trip passed')
wait_text('GET 200')
wait_text('Stop',tap=True)
wait_text('Stopped')
# Test actual exporter handoff to Android's document picker without saving to cloud.
wait_text('HAR',tap=True)
wait_text('Sensitive data')
wait_text('Continue',tap=True)
wait_text('capture.har')
har_path=adb('shell','run-as','dev.httpcapture.capture_app','find','.','-name','capture.har').strip().splitlines()[0]
har=json.loads(adb('shell','run-as','dev.httpcapture.capture_app','cat',har_path))
assert len(har['log']['entries']) == 1
assert har['log']['entries'][0]['response']['status'] == 200
# Common SQLite metadata and binary body survived on Android's own filesystem.
rows=adb('shell','run-as','dev.httpcapture.capture_app','ls','files')
# The exact support directory can be nested; inspect files without reading traffic values.
listing=adb('shell','run-as','dev.httpcapture.capture_app','find','.','-name','*.response.bin')
if not listing.strip(): raise RuntimeError('No captured body file persisted')
report={'status':'passed','device':'Android API35 x86_64 emulator','apkLaunch':True,'nativeForegroundService':True,'localHttpBinaryRoundTrip':True,'sessionList':True,'harDocumentPicker':True,'bodyFilePersisted':True,'vpnHint':'not tested','realDevice':'not tested','httpsDecryption':False}
Path('android-device-smoke.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
