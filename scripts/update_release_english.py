"""Update descriptions and add an English guide without modifying app packages."""
import hashlib
import json
from pathlib import Path
import subprocess
import os
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MARKER = '<!-- HTTP_CAPTURE_ENGLISH -->'
RELEASE_ID = 426404340
TAG = 'v0.1.0-preview.20261028'
SOURCE = 'ff41434306fb65004d379ace2fcb614b1890a4e3'


def gh(*args):
    return subprocess.check_output(['gh', *map(str, args)], text=True, timeout=180)


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    endpoint = f'repos/{repo}/releases/{RELEASE_ID}'
    before = json.loads(gh('api', endpoint))
    if (before['tag_name'] != TAG or before['draft'] or before['target_commitish'] != SOURCE):
        raise RuntimeError('Unexpected release target')
    existing = {a['name']: (a['id'], a['size'], a.get('digest')) for a in before['assets']}
    english = (ROOT/'release/notes.en.md').read_text().replace('{{SOURCE_SHA}}', SOURCE).strip()
    korean = before.get('body', '').split('\n\n---\n\n' + MARKER)[0].rstrip()
    body = korean + '\n\n---\n\n' + MARKER + '\n\n' + english + '\n'
    guide = ROOT/'release/INSTALL.en.md'
    guide_digest = 'sha256:' + hashlib.file_digest(guide.open('rb'), 'sha256').hexdigest()
    prior = next((a for a in before['assets'] if a['name'] == guide.name), None)
    if prior:
        if prior.get('digest') != guide_digest:
            raise RuntimeError('An English guide with different contents already exists; no asset overwritten')
    else:
        gh('release', 'upload', TAG, guide, '--repo', repo)
    with tempfile.TemporaryDirectory() as directory:
        request = Path(directory)/'description.json'
        request.write_text(json.dumps({'body': body}))
        gh('api', '--method', 'PATCH', endpoint, '--input', request)
    after = json.loads(gh('api', endpoint))
    actual = {a['name']: (a['id'], a['size'], a.get('digest')) for a in after['assets']}
    if after['body'] != body or any(actual.get(k) != v for k, v in existing.items()):
        raise RuntimeError('Description or original asset verification failed')
    if actual[guide.name][2] != guide_digest:
        raise RuntimeError('English guide digest mismatch')
    print(after['html_url'])


if __name__ == '__main__':
    main()
