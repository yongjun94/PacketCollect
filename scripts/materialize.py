#!/usr/bin/env python3
"""Build a readable platform checkout from the repository's source archive and overlays.

This tool creates a new directory; it never replaces an existing checkout.
"""
import argparse
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[1]


def unpack_source(archive, staging):
    with ZipFile(archive) as z:
        for member in z.infolist():
            name = PurePosixPath(member.filename.replace('\\', '/'))
            mode = member.external_attr >> 16
            if (name.is_absolute() or not name.parts or name.parts[0] != 'http-capture'
                    or '..' in name.parts or ':' in member.filename or stat.S_ISLNK(mode)):
                raise ValueError(f'Unsafe source archive path: {member.filename}')
        z.extractall(staging)
    root = staging / 'http-capture'
    if not (root / 'packages/capture_core').is_dir():
        raise ValueError('Source archive is missing capture_core')
    return root


def apply_overlay(source, target):
    if not source.is_dir():
        raise FileNotFoundError(f'Missing overlay: {source}')
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError(f'Symlink in overlay: {source}')
    shutil.copytree(source, target, dirs_exist_ok=True)


def materialize(repo, platform, destination, generate_android=False):
    destination = Path(os.path.abspath(destination))
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f'Destination already exists: {destination}')
    if platform == 'android' and not generate_android:
        raise ValueError('Android needs --generate-android and a working Flutter SDK')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='http-capture-', dir=destination.parent) as temp:
        root = unpack_source(repo / 'HTTP-Capture-Source.zip', Path(temp))
        apply_overlay(repo / 'fixes', root)
        if platform == 'windows':
            shutil.copy2(repo / 'build_desktop.py', root / 'scripts/build_desktop.py')
        elif platform == 'macos':
            apply_overlay(repo / 'macos-fixes', root)
        else:
            app = root / 'apps/capture_app'
            subprocess.run(['flutter', 'create', '--platforms', 'android', '--org', 'dev.httpcapture',
                            '--project-name', 'capture_app', '--no-pub', '.'], cwd=app, check=True)
            apply_overlay(repo / 'android-fixes', root)
            native = repo / 'android-native'
            main = app / 'android/app/src/main'
            main.mkdir(parents=True, exist_ok=True)
            shutil.copy2(native / 'AndroidManifest.xml', main / 'AndroidManifest.xml')
            kotlin = main / 'kotlin/dev/httpcapture/capture_app'
            kotlin.mkdir(parents=True, exist_ok=True)
            for source in native.glob('*.kt'):
                shutil.copy2(source, kotlin / source.name)
            gradle = main.parent.parent / 'build.gradle.kts'
            text = gradle.read_text(encoding='utf-8')
            text = text.replace('minSdk = flutter.minSdkVersion', 'minSdk = 29')
            text = text.replace('applicationId = "dev.httpcapture.capture_app"',
                                'applicationId = "dev.httpcapture.capture_app.all"')
            if 'minSdk = 29' not in text or 'dev.httpcapture.capture_app.all' not in text:
                raise RuntimeError('Unexpected Flutter Android Gradle template; no output was written.')
            text += '\ndependencies { implementation("org.bouncycastle:bcpkix-jdk15to18:1.86") }\n'
            gradle.write_text(text, encoding='utf-8')
        # Rename only after every step succeeded. The temporary directory is on the same filesystem.
        root.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platform', choices=['windows', 'macos', 'android'])
    parser.add_argument('--output', type=Path, required=True, help='New output directory; must not exist')
    parser.add_argument('--generate-android', action='store_true', help='Run flutter create for Android')
    args = parser.parse_args()
    try:
        print(materialize(REPO, args.platform, args.output, args.generate_android))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Unable to prepare project: {exc}\n')


if __name__ == '__main__':
    main()
