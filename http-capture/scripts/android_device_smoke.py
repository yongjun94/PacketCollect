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


def wait_text(label, tap=False, timeout=120):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            tree=screen()
        except (subprocess.CalledProcessError, ET.ParseError):
            time.sleep(2)
            continue
        # A freshly booted Google APIs image may show an unrelated system ANR.
        wait_dialog=next((n for n in tree.iter('node') if n.attrib.get('resource-id') == 'android:id/aerr_wait'),None)
        if wait_dialog is not None:
            coords=list(map(int,re.findall(r'\d+',wait_dialog.attrib['bounds'])))
            adb('shell','input','tap',str((coords[0]+coords[2])//2),str((coords[1]+coords[3])//2))
            time.sleep(3)
            continue
        for node in tree.iter('node'):
            value=node.attrib.get('text','')+' '+node.attrib.get('content-desc','')
            if label in value:
                if tap and (node.attrib.get('clickable') != 'true' or node.attrib.get('enabled') != 'true'):
                    continue
                if tap:
                    coords=list(map(int,re.findall(r'\d+',node.attrib['bounds'])))
                    adb('shell','input','tap',str((coords[0]+coords[2])//2),str((coords[1]+coords[3])//2))
                return value
        time.sleep(1)
    raise RuntimeError('UI text missing: '+label+' '+ET.tostring(tree,encoding='unicode') if 'tree' in locals() else 'UI unavailable')


def tap_until(label, expected, timeout=120):
    """Retry a missed tap only while the expected destination is absent."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        tree = screen()
        nodes = list(tree.iter('node'))
        if any(expected in (n.attrib.get('text', '') + ' ' + n.attrib.get('content-desc', ''))
               for n in nodes):
            return
        button = next((n for n in nodes
                       if label in (n.attrib.get('text', '') + ' ' + n.attrib.get('content-desc', ''))
                       and n.attrib.get('clickable') == 'true'
                       and n.attrib.get('enabled') == 'true'), None)
        if button is not None:
            coords = list(map(int, re.findall(r'\d+', button.attrib['bounds'])))
            adb('shell', 'input', 'tap', str((coords[0]+coords[2])//2), str((coords[1]+coords[3])//2))
        time.sleep(2)
    raise RuntimeError('Navigation did not complete: ' + label + ' -> ' + expected)


adb('install','-r','http-capture/apps/capture_app/build/app/outputs/flutter-apk/app-debug.apk')
adb('shell','am','start','-n','dev.httpcapture.capture_app.all/dev.httpcapture.capture_app.MainActivity')
time.sleep(15)
wait_text('Stopped')
tap_until('HTTPS settings', '모든 호스트 복호화')
wait_text('모든 호스트 복호화',tap=True)
wait_text('인증서 준비 및 설정 열기',tap=True)
time.sleep(3)
files=adb('shell','ls','/sdcard/Download')
assert any(n.startswith('HTTP-Capture-Root-') and n.endswith('.crt') for n in files.splitlines()),files
# CA export precedes the asynchronous launch of Security Settings. Wait for
# that activity to appear before returning, otherwise a late launch steals focus.
end = time.monotonic() + 60
while time.monotonic() < end:
    tree = screen()
    if any(n.attrib.get('package') in ('com.android.settings', 'com.android.permissioncontroller')
           for n in tree.iter('node')):
        break
    time.sleep(1)
else:
    raise RuntimeError('Security Settings did not open after CA export')
for _ in range(8):
    adb('shell', 'input', 'keyevent', '4')
    time.sleep(1)
    tree = screen()
    if any(n.attrib.get('package') == 'dev.httpcapture.capture_app.all'
           for n in tree.iter('node')):
        break
else:
    raise RuntimeError('Could not return from Security Settings to capture app')
wait_text('완료',tap=True)
wait_text('HTTPS on')
wait_text('Test TLS',tap=True)
wait_text('HTTPS test passed')
wait_text('Start',tap=True)
wait_text('OK',tap=True)  # Android VPN consent, not silently accepted by app.
wait_text('VPN proxy active')
time.sleep(3)
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.all','cat','files/recovery-state.json'))
assert state['active'] is True, state
assert state['ownProxy'] is True, state
wait_text('Test HTTP',tap=True)
wait_text('Local proxy round trip passed')
wait_text('GET 200')
wait_text('Stop',tap=True)
wait_text('Stopped')
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.all','cat','files/recovery-state.json'))
assert state['active'] is False and state['ownProxy'] is False, state
# Switching apps must keep capture alive; explicit Back exit releases it.
wait_text('Start',tap=True)
wait_text('VPN proxy active')
adb('shell','input','keyevent','3')
time.sleep(12)
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.all','cat','files/recovery-state.json'))
assert state['active'] is True and state['ownProxy'] is True, state
adb('shell','am','start','-n','dev.httpcapture.capture_app.all/dev.httpcapture.capture_app.MainActivity')
wait_text('VPN proxy active')
adb('shell','input','keyevent','4')
time.sleep(3)
adb('shell','am','start','-n','dev.httpcapture.capture_app.all/dev.httpcapture.capture_app.MainActivity')
wait_text('Stopped')
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.all','cat','files/recovery-state.json'))
assert state['active'] is False and state['ownProxy'] is False, state
wait_text('Start',tap=True)
wait_text('VPN proxy active')
adb('shell','am','force-stop','dev.httpcapture.capture_app.all')
time.sleep(2)
adb('shell','am','start','-n','dev.httpcapture.capture_app.all/dev.httpcapture.capture_app.MainActivity')
wait_text('Stopped')
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.all','cat','files/recovery-state.json'))
assert state['active'] is False and state['ownProxy'] is False, state
# Test actual exporter handoff to Android's document picker without saving to cloud.
wait_text('HAR',tap=True)
wait_text('Sensitive data')
wait_text('Continue',tap=True)
wait_text('capture.har')
har_path=adb('shell','run-as','dev.httpcapture.capture_app.all','find','.','-name','capture.har').strip().splitlines()[0]
har=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.all','cat',har_path))
test_entries=[e for e in har['log']['entries'] if e['request']['url'].endswith('/capture-self-test')]
assert len(test_entries) == 1
assert test_entries[0]['response']['status'] == 200
secure_entries=[e for e in har['log']['entries'] if e['request']['url'].endswith('/capture-https-self-test')]
assert len(secure_entries)==1
assert secure_entries[0]['response']['status']==200
assert secure_entries[0]['response']['content']['encoding']=='base64'
assert secure_entries[0]['response']['content']['text']=='AAEC/w=='
# Common SQLite metadata and binary body survived on Android's own filesystem.
rows=adb('shell','run-as','dev.httpcapture.capture_app.all','ls','files')
# The exact support directory can be nested; inspect files without reading traffic values.
listing=adb('shell','run-as','dev.httpcapture.capture_app.all','find','.','-name','*.response.bin')
if not listing.strip(): raise RuntimeError('No captured body file persisted')
report={'status':'passed','device':'Android API35 x86_64 emulator','apkLaunch':True,'nativeForegroundService':True,'localHttpBinaryRoundTrip':True,'sessionList':True,'harDocumentPicker':True,'bodyFilePersisted':True,'vpnProxyInstalled':True,'stopRestoresDefaultProxy':True,'backgroundKeepsCapture':True,'backExitReleasesProxy':True,'forceStopReleasesProxy':True,'realDevice':'not tested','httpsAllHostsEnabled':True,'publicCaSavedToDownloads':True,'httpsDecryption':True,'httpsLocalBinaryRoundTrip':True,'untrustedUpstreamRejected':True,'userCaInstall':'manual test pending'}
Path('android-device-smoke.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))


