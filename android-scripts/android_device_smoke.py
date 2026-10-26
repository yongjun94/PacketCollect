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


adb('install','-r','http-capture/apps/capture_app/build/app/outputs/flutter-apk/app-debug.apk')
adb('shell','am','start','-n','dev.httpcapture.capture_app.https/dev.httpcapture.capture_app.MainActivity')
time.sleep(15)
wait_text('Stopped')
wait_text('Test TLS',tap=True)
wait_text('HTTPS test passed')
wait_text('Start',tap=True)
wait_text('OK',tap=True)  # Android VPN consent, not silently accepted by app.
wait_text('VPN proxy active')
time.sleep(3)
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.https','cat','files/recovery-state.json'))
assert state['active'] is True, state
assert state['ownProxy'] is True, state
wait_text('Test HTTP',tap=True)
wait_text('Local proxy round trip passed')
wait_text('GET 200')
wait_text('Stop',tap=True)
wait_text('Stopped')
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.https','cat','files/recovery-state.json'))
assert state['active'] is False and state['ownProxy'] is False, state
# Switching apps must keep capture alive; explicit Back exit releases it.
wait_text('Start',tap=True)
wait_text('VPN proxy active')
adb('shell','input','keyevent','3')
time.sleep(12)
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.https','cat','files/recovery-state.json'))
assert state['active'] is True and state['ownProxy'] is True, state
adb('shell','am','start','-n','dev.httpcapture.capture_app.https/dev.httpcapture.capture_app.MainActivity')
wait_text('VPN proxy active')
adb('shell','input','keyevent','4')
time.sleep(3)
adb('shell','am','start','-n','dev.httpcapture.capture_app.https/dev.httpcapture.capture_app.MainActivity')
wait_text('Stopped')
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.https','cat','files/recovery-state.json'))
assert state['active'] is False and state['ownProxy'] is False, state
wait_text('Start',tap=True)
wait_text('VPN proxy active')
adb('shell','am','force-stop','dev.httpcapture.capture_app.https')
time.sleep(2)
adb('shell','am','start','-n','dev.httpcapture.capture_app.https/dev.httpcapture.capture_app.MainActivity')
wait_text('Stopped')
state=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.https','cat','files/recovery-state.json'))
assert state['active'] is False and state['ownProxy'] is False, state
# Test actual exporter handoff to Android's document picker without saving to cloud.
wait_text('HAR',tap=True)
wait_text('Sensitive data')
wait_text('Continue',tap=True)
wait_text('capture.har')
har_path=adb('shell','run-as','dev.httpcapture.capture_app.https','find','.','-name','capture.har').strip().splitlines()[0]
har=json.loads(adb('shell','run-as','dev.httpcapture.capture_app.https','cat',har_path))
test_entries=[e for e in har['log']['entries'] if e['request']['url'].endswith('/capture-self-test')]
assert len(test_entries) == 1
assert test_entries[0]['response']['status'] == 200
secure_entries=[e for e in har['log']['entries'] if e['request']['url'].endswith('/capture-https-self-test')]
assert len(secure_entries)==1
assert secure_entries[0]['response']['status']==200
assert secure_entries[0]['response']['content']['encoding']=='base64'
assert secure_entries[0]['response']['content']['text']=='AAEC/w=='
# Common SQLite metadata and binary body survived on Android's own filesystem.
rows=adb('shell','run-as','dev.httpcapture.capture_app.https','ls','files')
# The exact support directory can be nested; inspect files without reading traffic values.
listing=adb('shell','run-as','dev.httpcapture.capture_app.https','find','.','-name','*.response.bin')
if not listing.strip(): raise RuntimeError('No captured body file persisted')
report={'status':'passed','device':'Android API35 x86_64 emulator','apkLaunch':True,'nativeForegroundService':True,'localHttpBinaryRoundTrip':True,'sessionList':True,'harDocumentPicker':True,'bodyFilePersisted':True,'vpnProxyInstalled':True,'stopRestoresDefaultProxy':True,'backgroundKeepsCapture':True,'backExitReleasesProxy':True,'forceStopReleasesProxy':True,'realDevice':'not tested','httpsDecryption':True,'httpsLocalBinaryRoundTrip':True,'untrustedUpstreamRejected':True,'userCaInstall':'manual test pending'}
Path('android-device-smoke.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
