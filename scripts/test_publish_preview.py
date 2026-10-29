import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('publish_preview', Path(__file__).with_name('publish_preview.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Tests(unittest.TestCase):
    def test_unverified_and_foreign_runs_are_rejected(self):
        build={'run_id':1,'workflow':'.github/workflows/windows-build.yml'}
        valid=dict(status='completed',conclusion='success',head_sha='known',head_branch='main',event='push',path=build['workflow'],head_repository={'full_name':'owner/repo'})
        module.validate_run(valid,build,'known','owner/repo')
        for key,value in [('status','in_progress'),('conclusion','failure'),('head_sha','other'),('event','pull_request'),('path','untrusted.yml'),('head_repository',{'full_name':'fork/repo'})]:
            changed=copy.deepcopy(valid);changed[key]=value
            with self.assertRaises(ValueError):module.validate_run(changed,build,'known','owner/repo')

    def test_desktop_only_release_scope(self):
        module.validate_builds([{'platform':'windows'}, {'platform':'macos'}])
        for platforms in ([], ['windows'], ['android','windows','macos'],
                          ['windows','windows'], ['macos','ios']):
            with self.assertRaises(ValueError):
                module.validate_builds([{'platform':p} for p in platforms])

    def test_wrong_platform_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'app.zip'
            with zipfile.ZipFile(path,'w') as z:z.writestr('README.txt','not an app')
            for platform in ('windows','macos','android'):
                with self.assertRaises(ValueError):module.check_payload(path,platform)
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('AndroidManifest.xml','fixture');z.writestr('classes.dex','fixture')
            module.check_payload(path,'android')
            with self.assertRaises(ValueError):module.check_payload(path,'windows')

if __name__=='__main__':unittest.main()
