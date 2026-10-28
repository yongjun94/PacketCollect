"""Collect installed package evidence, not a legal approval or native SBOM proof."""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlparse, unquote
from urllib.request import url2pathname


def collect(output, pub_config=None):
    output.mkdir(parents=True, exist_ok=True)
    records=[]
    for dist in sorted(metadata.distributions(),key=lambda d:d.metadata['Name'].lower()):
        name=dist.metadata['Name'];version=dist.version
        license=dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'UNRESOLVED'
        files=[]
        for file in dist.files or ():
            if re.search(r'(^|/)(licen[cs]e|copying|notice)[^/]*$',str(file),re.I):
                source=Path(dist.locate_file(file))
                if source.is_file():
                    dest=output/'texts'/name/str(file)
                    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
                    files.append(str(dest.relative_to(output)))
        records.append({'ecosystem':'pypi','name':name,'version':version,'licenseMetadata':license,'notices':files})
    if pub_config:
        config=json.loads(pub_config.read_text())
        for pkg in config['packages']:
            uri=pkg['rootUri'];parsed=urlparse(uri)
            source=Path(url2pathname(parsed.path)) if parsed.scheme=='file' else (pub_config.parent/uri).resolve()
            if pkg['name'] in ('capture_app','capture_core','capture_export'):continue
            license_file=source/'LICENSE'
            files=[]
            if license_file.exists():
                dest=output/'texts/dart'/pkg['name']/'LICENSE';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(license_file,dest)
                files=[str(dest.relative_to(output))]
            # pubspec.yaml version is evidence; SDK packages use the SDK version inventory.
            version='SDK'
            pubspec=source/'pubspec.yaml'
            if pubspec.exists():
                match=re.search(r"^version:\s*[\'\"]?([^\s\'\"]+)",pubspec.read_text(),re.M)
                if match:version=match[1]
            records.append({'ecosystem':'pub','name':pkg['name'],'version':version,'licenseMetadata':'See full text' if files else 'UNRESOLVED','notices':files})
    (output/'THIRD_PARTY_NOTICES.json').write_text(json.dumps(records,indent=2))
    components=[{'type':'library','name':r['name'],'version':r['version'],'purl':f"pkg:{r['ecosystem']}/{r['name']}@{r['version']}",'licenses':[{'license':{'name':r['licenseMetadata'][:1000]}}]} for r in records]
    (output/'sbom.cdx.json').write_text(json.dumps({'bomFormat':'CycloneDX','specVersion':'1.5','version':1,'components':components},indent=2))
    unresolved=[r['name'] for r in records if not r['notices'] or r['licenseMetadata']=='UNRESOLVED']
    (output/'REVIEW_REQUIRED.md').write_text('Installed-package evidence only. Native Rust/OpenSSL/SQLite, Python runtime, Flutter engine, build tool exceptions and platform-specific binaries require separate review.\n\nMissing notice or metadata evidence: '+', '.join(unresolved)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('--pub-config',type=Path)
    args=parser.parse_args();collect(args.output,args.pub_config)
