"""Update bilingual desktop support notes, preserving every existing asset."""
import json
from pathlib import Path
import subprocess
import os
import tempfile

ROOT = Path(__file__).resolve().parents[1]
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
    def assets(release):
        return {a['name']: (a['id'], a['size'], a.get('digest')) for a in release['assets']}
    existing = assets(before)
    status = (ROOT/'release/distribution-status.md').read_text().strip()
    korean = (ROOT/'release/notes.ko.md').read_text().replace('{{SOURCE_SHA}}', SOURCE).strip()
    english = (ROOT/'release/notes.en.md').read_text().replace('{{SOURCE_SHA}}', SOURCE).strip()
    body = status + '\n\n' + korean + '\n\n---\n\n' + english + '\n'
    with tempfile.TemporaryDirectory() as directory:
        request = Path(directory)/'description.json'
        request.write_text(json.dumps({'body': body}))
        gh('api', '--method', 'PATCH', endpoint, '--input', request)
    after = json.loads(gh('api', endpoint))
    if after['body'] != body or assets(after) != existing:
        raise RuntimeError('Description or original asset verification failed')
    print(after['html_url'])


if __name__ == '__main__':
    main()
