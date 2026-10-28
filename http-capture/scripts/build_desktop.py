"""Build and validate an unsigned development bundle on its target OS."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, env=None):
    args = [str(a) for a in args]
    # Windows batch files require cmd.exe; list2cmdline quotes spaces correctly.
    if os.name == 'nt' and Path(args[0]).suffix.lower() in ('.bat', '.cmd'):
        if any(any(c in arg for c in ('\"', '%', '\r', '\n')) for arg in args):
            raise ValueError('Batch build arguments contain unsupported shell characters')
        quoted = ' '.join('\"' + arg + '\"' for arg in args)
        shell = subprocess.list2cmdline([os.environ.get('COMSPEC', 'cmd.exe')])
        args = shell + ' /d /v:off /s /c \"' + quoted + '\"'
    subprocess.run(args, cwd=cwd, env=env, check=True)


def python_env(path):
    venv.EnvBuilder(with_pip=True, clear=True).create(path)
    return path / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def copy_windows_runtime(output):
    program_files = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
    vswhere = Path(program_files) / 'Microsoft Visual Studio/Installer/vswhere.exe'
    if not vswhere.is_file():
        raise RuntimeError('Visual Studio Installer vswhere.exe missing')
    installations = json.loads(subprocess.check_output(
        [str(vswhere), '-products', '*', '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-format', 'json', '-utf8'], text=True, encoding='utf-8'))
    candidates = []
    for installation in installations:
        redist = Path(installation['installationPath']) / 'VC/Redist/MSVC'
        candidates.extend(redist.glob('*/x64/Microsoft.VC*.CRT'))
    if not candidates:
        raise RuntimeError('Visual C++ x64 redistributable directory missing')
    def version(folder):
        return tuple(int(v) for v in folder.parents[1].name.split('.'))
    crt = sorted(candidates, key=version)[-1]
    copied = []
    for dll in crt.glob('*.dll'):
        shutil.copy2(dll, output / dll.name)
        copied.append(dll.name)
    for required in ('vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll'):
        if required not in copied:
            raise RuntimeError(f'Missing required VC++ runtime {required}')
    return copied


def validate_bundle(output, target):
    required = (['HTTP-Capture.exe', 'flutter_windows.dll', 'sqlite3.dll',
                 'proxy/http-capture-proxy.exe', 'data/icudtl.dat', 'data/flutter_assets']
                if target == 'windows' else ['Contents/MacOS/capture_app', 'Contents/Resources/proxy/http-capture-proxy'])
    for name in required:
        if not (output / name).exists():
            raise RuntimeError(f'Incomplete bundle: {name}')
    # CA material is created on the destination machine, never packaged.
    for file in output.rglob('*'):
        if file.is_file() and file.name.startswith('mitmproxy-ca'):
            raise RuntimeError(f'Installation CA material found in bundle: {file.name}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target', choices=['windows', 'macos'])
    args = parser.parse_args()
    if (args.target == 'windows' and sys.platform != 'win32') or (args.target == 'macos' and sys.platform != 'darwin'):
        raise SystemExit('Run on the target OS. Flutter and PyInstaller do not build this Windows bundle on Linux.')
    if sys.version_info[:2] != (3, 12):
        raise SystemExit('Build requires Python 3.12.x')
    if args.target == 'macos' and platform.machine() != 'arm64':
        raise SystemExit('This preview requires a native Apple Silicon runner')
    flutter = shutil.which('flutter')
    if not flutter:
        raise SystemExit('Flutter 3.35.5 required on PATH')
    build_python = python_env(ROOT / '.build/python')
    runtime_python = python_env(ROOT / '.build/runtime-inventory')
    lock = ROOT / 'engines/desktop_proxy/requirements.lock'
    for python in (build_python, runtime_python):
        run(python, '-m', 'pip', 'install', '--require-hashes', '-r', lock)
    run(build_python, '-m', 'pip', 'install', '--require-hashes', '-r', ROOT / 'scripts/build-requirements.lock')
    app = ROOT / 'apps/capture_app'
    run(flutter, 'pub', 'get', '--enforce-lockfile', cwd=app)
    run(flutter, 'analyze', cwd=app)
    # Build first: the desktop SQLite DLL is needed by Flutter/Dart tests on Windows.
    run(flutter, 'build', args.target, '--release', cwd=app)
    if args.target == 'windows':
        source = app / 'build/windows/x64/runner/Release'
        output = ROOT / 'dist/HTTP-Capture-Windows'
    else:
        source = app / 'build/macos/Build/Products/Release/capture_app.app'
        output = ROOT / 'dist/HTTP-Capture.app'
    test_env = dict(os.environ)
    test_env['PATH'] = str(source) + os.pathsep + test_env.get('PATH', '')
    run(flutter, 'test', 'test/desktop', '--reporter', 'expanded', cwd=app, env=test_env)
    for package in ('capture_core', 'capture_export'):
        cwd = ROOT / 'packages' / package
        run(flutter, 'pub', 'get', '--enforce-lockfile', cwd=cwd, env=test_env)
        run(flutter, 'analyze', cwd=cwd, env=test_env)
    run(flutter, 'pub', 'run', 'test', '--reporter', 'expanded', cwd=ROOT / 'packages/capture_export', env=test_env)
    engine = ROOT / 'engines/desktop_proxy'
    run(build_python, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--name', 'http-capture-proxy',
        '--paths', engine / 'src', '--collect-all', 'mitmproxy', '--collect-all', 'mitmproxy_rs',
        '--collect-all', {'windows': 'mitmproxy_windows', 'macos': 'mitmproxy_macos'}[args.target],
        '--distpath', ROOT / '.build/frozen', '--workpath', ROOT / '.build/pyinstaller', '--specpath', ROOT / '.build', engine / 'entrypoint.py')
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(source, output, symlinks=True)
    proxy = output / ('proxy' if args.target == 'windows' else 'Contents/Resources/proxy')
    shutil.copytree(ROOT / '.build/frozen/http-capture-proxy', proxy, symlinks=True)
    assets = output if args.target == 'windows' else output / 'Contents/Resources'
    runtimes = copy_windows_runtime(output) if args.target == 'windows' else []
    run(runtime_python, ROOT / 'scripts/collect_notices.py', assets / 'licenses', '--pub-config', app / '.dart_tool/package_config.json')
    shutil.copytree(ROOT / 'docs', assets / 'resources/docs')
    validate_bundle(output, args.target)
    # A packaged engine must start with the bundled runtime, not the development Python.
    run(build_python, ROOT / 'scripts/smoke_packaged.py', '--engine', proxy / ('http-capture-proxy.exe' if args.target == 'windows' else 'http-capture-proxy'),
        '--report', assets / 'resources/engine-smoke.json')
    files = []
    for file in sorted(output.rglob('*')):
        if file.is_file():
            files.append({'path': file.relative_to(output).as_posix(), 'size': file.stat().st_size,
                          'sha256': hashlib.file_digest(file.open('rb'), 'sha256').hexdigest()})
    manifest = {'target': args.target, 'architecture': 'x64' if args.target == 'windows' else 'arm64',
                'signed': False, 'status': 'development-build', 'vcRuntimeFiles': runtimes,
                'inventoryStage': 'before-final-signing', 'manualAcceptance': 'pending', 'runtimeLockSha256': hashlib.sha256(lock.read_bytes()).hexdigest(), 'files': files}
    (assets / 'resources/build-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if args.target == 'macos':
        run('/usr/bin/codesign', '--force', '--sign', '-', output)
        run('/usr/bin/codesign', '--verify', '--deep', '--strict', output)
        run('/usr/bin/lipo', output / 'Contents/MacOS/capture_app', '-verify_arch', 'arm64')
        run('/usr/bin/lipo', proxy / 'http-capture-proxy', '-verify_arch', 'arm64')
        archive = str(output.parent / 'HTTP-Capture-macOS-arm64.zip')
        run('/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', output, archive)
    else:
        archive = shutil.make_archive(str(output), 'zip', root_dir=output.parent, base_dir=output.name)
    print(f'Created unsigned development bundle: {archive}. Manual Windows/Fiddler/DevTools acceptance remains pending.')


if __name__ == '__main__':
    main()

