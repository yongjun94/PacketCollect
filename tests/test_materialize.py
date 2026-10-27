import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

spec = importlib.util.spec_from_file_location('materialize', Path(__file__).resolve().parents[1] / 'scripts/materialize.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MaterializeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        with ZipFile(self.repo / 'HTTP-Capture-Source.zip', 'w') as z:
            z.writestr('http-capture/packages/capture_core/pubspec.yaml', 'name: capture_core')
            z.writestr('http-capture/packages/capture_export/lib/export.dart', 'shared exporter')
            z.writestr('http-capture/apps/capture_app/lib/app.dart', 'base app')
            z.writestr('http-capture/scripts/old.txt', 'original')
        for name in ['fixes', 'macos-fixes', 'android-fixes', 'android-native']:
            (self.repo / name).mkdir()
        self.put('fixes/apps/capture_app/lib/app.dart', 'windows fix')
        self.put('macos-fixes/apps/capture_app/lib/app.dart', 'mac fix')
        self.put('android-fixes/apps/capture_app/lib/main.dart', 'android entry')
        self.put('android-native/MainActivity.kt', 'native activity')
        self.put('android-native/AndroidManifest.xml', 'native manifest')
        self.put('build_desktop.py', 'windows build')

    def tearDown(self):
        self.temp.cleanup()

    def put(self, path, content):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def test_windows_and_macos_have_shared_packages_and_correct_override(self):
        for platform, expected in [('windows', 'windows fix'), ('macos', 'mac fix')]:
            out = self.base / platform
            m.materialize(self.repo, platform, out)
            self.assertEqual((out / 'apps/capture_app/lib/app.dart').read_text(), expected)
            self.assertEqual((out / 'packages/capture_export/lib/export.dart').read_text(), 'shared exporter')
        self.assertEqual((self.base / 'windows/scripts/build_desktop.py').read_text(), 'windows build')

    def test_existing_destination_is_never_replaced(self):
        dest = self.base / 'existing'
        dest.mkdir()
        (dest / 'important').write_text('keep')
        with self.assertRaises(FileExistsError):
            m.materialize(self.repo, 'windows', dest)
        self.assertEqual((dest / 'important').read_text(), 'keep')

    def test_android_requires_flutter_and_assembles_native_runner(self):
        out = self.base / 'android'
        with self.assertRaises(ValueError):
            m.materialize(self.repo, 'android', out)
        def fake_flutter(args, cwd, check):
            gradle = cwd / 'android/app/build.gradle.kts'
            gradle.parent.mkdir(parents=True)
            gradle.write_text('minSdk = flutter.minSdkVersion\napplicationId = "dev.httpcapture.capture_app"')
        with patch.object(m.subprocess, 'run', side_effect=fake_flutter):
            m.materialize(self.repo, 'android', out, True)
        self.assertEqual((out / 'apps/capture_app/lib/main.dart').read_text(), 'android entry')
        self.assertEqual((out / 'apps/capture_app/android/app/src/main/kotlin/dev/httpcapture/capture_app/MainActivity.kt').read_text(), 'native activity')
        gradle = (out / 'apps/capture_app/android/app/build.gradle.kts').read_text()
        self.assertIn('minSdk = 29', gradle)
        self.assertIn('dev.httpcapture.capture_app.all', gradle)
        self.assertIn('bcpkix-jdk15to18:1.86', gradle)

    def test_zip_slip_is_rejected(self):
        with ZipFile(self.repo / 'HTTP-Capture-Source.zip', 'a') as z:
            z.writestr('http-capture/../../escape.txt', 'unsafe')
        with self.assertRaises(ValueError):
            m.materialize(self.repo, 'windows', self.base / 'bad')
        self.assertFalse((self.base / 'escape.txt').exists())
        self.assertFalse((self.base / 'bad').exists())


if __name__ == '__main__':
    unittest.main()
