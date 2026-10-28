"""Build recipe contract tests; these do not constitute a Windows build."""
import importlib.util
import json
from pathlib import Path
import types
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('build_desktop', ROOT / 'scripts/build_desktop.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_bundle_validation_rejects_missing_runtime_and_ca(tmp_path):
    with pytest.raises(RuntimeError, match='Incomplete bundle'):
        build.validate_bundle(tmp_path, 'windows')
    for name in ['HTTP-Capture.exe', 'flutter_windows.dll', 'sqlite3.dll',
                 'proxy/http-capture-proxy.exe', 'data/icudtl.dat']:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'test-fixture')
    (tmp_path / 'data/flutter_assets').mkdir()
    build.validate_bundle(tmp_path, 'windows')
    (tmp_path / 'mitmproxy-ca.pem').write_text('fixture private key sentinel')
    with pytest.raises(RuntimeError, match='CA material'):
        build.validate_bundle(tmp_path, 'windows')


def test_windows_runtime_requires_complete_app_local_crt(tmp_path, monkeypatch):
    installer = tmp_path / 'Program Files (x86)/Microsoft Visual Studio/Installer'
    installer.mkdir(parents=True)
    (installer / 'vswhere.exe').touch()
    vs = tmp_path / 'Visual Studio'
    crt = vs / 'VC/Redist/MSVC/14.44.35211/x64/Microsoft.VC143.CRT'
    crt.mkdir(parents=True)
    for name in ('vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll'):
        (crt / name).write_bytes(name.encode())
    monkeypatch.setenv('ProgramFiles(x86)', str(tmp_path / 'Program Files (x86)'))
    monkeypatch.setattr(build.subprocess, 'check_output', lambda *a, **kw: json.dumps([{'installationPath': str(vs)}]))
    output = tmp_path / 'bundle'
    output.mkdir()
    result = build.copy_windows_runtime(output)
    assert sorted(result) == ['msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll']
    (crt / 'msvcp140.dll').unlink()
    with pytest.raises(RuntimeError, match='Missing required VC'):
        build.copy_windows_runtime(output)


def test_windows_batch_launch_preserves_spaced_paths(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(build, 'os', types.SimpleNamespace(name='nt', environ={'COMSPEC': r'C:\Windows\System32\cmd.exe'}))
    monkeypatch.setattr(build.subprocess, 'run', lambda args, **kw: calls.append((args, kw)))
    flutter = tmp_path / 'Flutter SDK/bin/flutter.bat'
    build.run(flutter, 'pub', 'get', '--enforce-lockfile')
    line, options = calls[0]
    assert f'/c ""{flutter}" "pub" "get" "--enforce-lockfile""' in line
    assert '/v:off' in line
    assert options['check'] is True
    with pytest.raises(ValueError, match='unsupported shell'):
        build.run(flutter, '%UNTRUSTED%')


def test_acl_sid_parsing_does_not_decode_localized_account_name(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(ROOT / 'engines/desktop_proxy/src'))
    import capture_proxy.config as config
    calls = []
    monkeypatch.setattr(config, 'os', types.SimpleNamespace(name='nt'))
    monkeypatch.setattr(config.subprocess, 'check_output', lambda *a, **kw: b'"computer\\\xff\xfe","S-1-5-21-1000"\r\n')
    monkeypatch.setattr(config.subprocess, 'run', lambda *a, **kw: calls.append(a[0]))
    config.secure_directory(tmp_path / 'capture')
    assert calls[0][-1] == '*S-1-5-21-1000:(OI)(CI)F'
