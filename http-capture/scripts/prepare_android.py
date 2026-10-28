"""Generate the pinned Flutter Android runner, then install the native engine.

Dart source is never generated or overwritten. The runner is build scaffolding;
the reviewed Android engine lives in engines/android_vpn.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def prepare(root=ROOT, runner=subprocess.run):
    app = root / 'apps/capture_app'
    target = app / 'android'
    if target.exists():
        raise SystemExit('Android runner already exists. Reuse it; remove only generated android/ to regenerate.')
    flutter = shutil.which('flutter')
    if not flutter:
        raise SystemExit('Flutter 3.35.5 must be on PATH')
    with tempfile.TemporaryDirectory() as directory:
        generated = Path(directory)
        runner([flutter, 'create', '--platforms', 'android', '--org', 'dev.httpcapture',
                '--project-name', 'capture_app', '--no-pub', str(generated)], check=True)
        shutil.copytree(generated / 'android', target)
    native = root / 'engines/android_vpn'
    source = target / 'app/src/main'
    shutil.copy2(native / 'AndroidManifest.xml', source / 'AndroidManifest.xml')
    kotlin = source / 'kotlin/dev/httpcapture/capture_app'
    kotlin.mkdir(parents=True, exist_ok=True)
    for file in native.glob('*.kt'):
        shutil.copy2(file, kotlin / file.name)
    gradle = target / 'app/build.gradle.kts'
    text = gradle.read_text().replace('minSdk = flutter.minSdkVersion', 'minSdk = 29')
    text = text.replace('applicationId = "dev.httpcapture.capture_app"', 'applicationId = "dev.httpcapture.capture_app.all"')
    text += '\ndependencies { implementation("org.bouncycastle:bcpkix-jdk15to18:1.86") }\n'
    gradle.write_text(text)


if __name__ == '__main__':
    prepare()
