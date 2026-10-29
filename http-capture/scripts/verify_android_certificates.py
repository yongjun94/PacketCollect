"""Validate public certificates produced by the actual Android Keystore issuer."""
import json
import subprocess
from pathlib import Path

PACKAGE = 'dev.httpcapture.capture_app.all'


def device_file(name):
    return subprocess.check_output(
        ['adb', 'shell', 'run-as', PACKAGE, 'cat',
         'files/certificate-profile-check/' + name], text=True)


def run(*args, accepted=True):
    result = subprocess.run(['openssl', *map(str, args)], text=True,
                            capture_output=True)
    if accepted and result.returncode:
        raise RuntimeError(result.stderr)
    if not accepted and result.returncode == 0:
        raise AssertionError('Invalid certificate unexpectedly verified')
    return result.stdout


def main():
    folder = Path('android-certificate-profile')
    folder.mkdir(exist_ok=True)
    report = json.loads(device_file('report.json'))
    assert report['status'] == 'passed'
    assert report['rootSkiAkiMatch'] is True
    assert report['leafSkiAkiSanEkuSignaturePkix'] is True
    assert report['privateKeysExported'] is False
    root = folder / 'root.pem'
    root.write_text(device_file('root.pem'))
    assert 'PRIVATE KEY' not in root.read_text()
    extensions = run('x509', '-in', root, '-noout', '-text')
    assert 'Subject Key Identifier' in extensions
    assert 'Authority Key Identifier' in extensions
    run('verify', '-check_ss_sig', '-x509_strict', '-CAfile', root, root)
    for index, host in enumerate(report['hosts']):
        leaf = folder / f'leaf-{index}.pem'
        leaf.write_text(device_file(f'leaf-{index}.pem'))
        assert 'PRIVATE KEY' not in leaf.read_text()
        text = run('x509', '-in', leaf, '-noout', '-text')
        assert 'Subject Key Identifier' in text
        assert 'Authority Key Identifier' in text
        target = '-verify_ip' if ':' in host or host.replace('.', '').isdigit() else '-verify_hostname'
        run('verify', '-x509_strict', '-purpose', 'sslserver', target, host,
            '-CAfile', root, leaf)
        run('verify', '-x509_strict', '-verify_hostname', 'wrong.invalid',
            '-CAfile', root, leaf, accepted=False)
        run('verify', '-no-CAfile', '-no-CApath', '-no-CAstore', leaf, accepted=False)
    report.update(opensslStrictChains=True, hostnameMismatchRejected=True,
                  missingTrustAnchorRejected=True, officeAppTrust='not tested')
    Path('android-certificate-profile.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
