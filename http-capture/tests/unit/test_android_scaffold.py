import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('prepare_android', Path(__file__).resolve().parents[2] / 'scripts/prepare_android.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Tests(unittest.TestCase):
    def test_generator_cannot_overwrite_dart_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dart = root / 'apps/capture_app/lib/main.dart'
            dart.parent.mkdir(parents=True)
            dart.write_text('original reviewed application')
            native = root / 'engines/android_vpn'
            native.mkdir(parents=True)
            (native/'AndroidManifest.xml').write_text('<manifest/>')
            def generate(command, **kwargs):
                project = Path(command[-1])
                (project/'lib').mkdir()
                (project/'lib/main.dart').write_text('generated template')
                gradle = project/'android/app/build.gradle.kts'
                gradle.parent.mkdir(parents=True)
                (project/'android/app/src/main').mkdir(parents=True)
                gradle.write_text('minSdk = flutter.minSdkVersion\napplicationId = "dev.httpcapture.capture_app"')
            with patch.object(module.shutil, 'which', return_value='/fake/flutter'):
                module.prepare(root, runner=generate)
            self.assertEqual(dart.read_text(), 'original reviewed application')
            with self.assertRaises(SystemExit):
                module.prepare(root, runner=generate)
            self.assertEqual(dart.read_text(), 'original reviewed application')

if __name__ == '__main__': unittest.main()
