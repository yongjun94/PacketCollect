"""Publish only named artifacts from successful, same-commit trusted CI runs.

Run inside the release workflow with its scoped GitHub token. Builds are not
rerun or repacked, so the uploaded runtime is exactly the tested CI payload.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def gh(*args, check=True):
    return subprocess.run(['gh', *map(str, args)], check=check, text=True,
                          capture_output=True, timeout=300)


def api(repo, endpoint):
    return json.loads(gh('api', f'repos/{repo}/{endpoint}').stdout)


def validate_run(run, build, sha, repo):
    if (run.get('status') != 'completed' or run.get('conclusion') != 'success'
            or run.get('head_sha') != sha or run.get('head_branch') != 'main'
            or run.get('event') != 'push' or run.get('path') != build['workflow']
            or run.get('head_repository', {}).get('full_name') != repo):
        raise ValueError('Build provenance validation failed for ' + str(build['run_id']))


def check_payload(path, platform):
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError('Corrupt payload: ' + bad)
        names = archive.namelist()
        expected = {'windows': '/HTTP-Capture.exe',
                    'macos': '/Contents/MacOS/capture_app',
                    'android': 'AndroidManifest.xml'}[platform]
        if not any(n.endswith(expected) for n in names):
            raise ValueError('Incorrect platform payload: ' + platform)
        if platform == 'android' and not any(re.fullmatch(r'classes\d*\.dex', n) for n in names):
            raise ValueError('APK has no compiled application')


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    plan = json.loads((ROOT / 'release/preview.json').read_text())
    tag, sha = plan['tag'], plan['source_sha']
    if not re.fullmatch(r'v\d+\.\d+\.\d+-preview\.\d{8}', tag) or not re.fullmatch('[0-9a-f]{40}', sha):
        raise ValueError('Invalid release version or source SHA')
    builds = plan['builds']
    if sorted(b['platform'] for b in builds) != ['android', 'macos', 'windows']:
        raise ValueError('Exactly one tested build for each platform is required')
    # Validate every run and artifact before any release mutation.
    for build in builds:
        validate_run(api(repo, f'actions/runs/{build["run_id"]}'), build, sha, repo)
        artifact = api(repo, f'actions/artifacts/{build["artifact_id"]}')
        if (artifact['name'] != build['artifact'] or artifact['expired']
                or artifact['workflow_run']['id'] != build['run_id']
                or artifact['workflow_run']['head_sha'] != sha):
            raise ValueError('Artifact is missing, expired, replaced or mismatched')
        for field in ('input', 'output'):
            if Path(build[field]).name != build[field]:
                raise ValueError('Payload filenames must be basenames')
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        assets = temp / 'assets'
        assets.mkdir()
        provenance = dict(source_sha=sha, release_workflow_sha=os.environ.get('GITHUB_SHA'),
                          status='development-preview', files=[])
        for build in builds:
            download = temp / build['platform']
            gh('run', 'download', build['run_id'], '--repo', repo,
               '--name', build['artifact'], '--dir', download)
            matches = list(download.rglob(build['input']))
            if len(matches) != 1 or not matches[0].is_file() or matches[0].is_symlink():
                raise ValueError('Expected one payload file: ' + build['input'])
            path = assets / build['output']
            shutil.copyfile(matches[0], path)
            check_payload(path, build['platform'])
            digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
            provenance['files'].append(dict(name=path.name, sha256=digest, size=path.stat().st_size,
                                            run_id=build['run_id'], artifact_id=build['artifact_id']))
        (assets/'SHA256SUMS.txt').write_text(''.join(f'{f["sha256"]}  {f["name"]}\n' for f in provenance['files']))
        (assets/'build-provenance.json').write_text(json.dumps(provenance, indent=2))
        shutil.copyfile(ROOT/'release/INSTALL.md', assets/'INSTALL.md')
        notes = temp/'notes.md'
        notes.write_text('# Windows / macOS / Android 다운로드\n\n'
                         '아래 Assets에서 운영체제에 맞는 파일을 선택하세요. 비공개 저장소 접근 권한이 필요합니다.\n\n'
                         '| 파일 | 대상 |\n|---|---|\n'
                         '| HTTP-Capture-Windows-x64.zip | Windows x64, 압축 해제 후 EXE 실행 |\n'
                         '| HTTP-Capture-macOS-arm64.zip | Mac Apple Silicon |\n'
                         '| HTTP-Capture-Android-preview.apk | Android 개발용 APK |\n\n'
                         'Windows 배포 서명 없음, Mac ad-hoc 서명/공증 없음, Android debug 서명입니다. '
                         '보안 정책을 우회하지 마세요. Python/Flutter SDK는 최종 사용자에게 필요하지 않습니다.\n\n'
                         '세 플랫폼 CI 빌드/테스트 및 API35 에뮬레이터 검증을 통과했습니다. '
                         '이번 구조의 실기기별 재검증과 Android 사용자 CA 설치는 별도 확인이 필요합니다. '
                         '시스템 프록시를 따르는 HTTP/HTTPS가 대상입니다. '
                         '설치·인증서·기존 APK 업데이트 주의사항은 INSTALL.md를 확인하세요.\n\n'
                         f'소스 커밋: `{sha}`\n\n'
                         'SHA256SUMS.txt와 build-provenance.json으로 배포 파일과 CI 출처를 확인할 수 있습니다.\n')
        # Keep incomplete uploads in a draft; publish only after all assets exist.
        gh('release', 'create', tag, *sorted(assets.iterdir()), '--repo', repo,
           '--target', sha, '--draft', '--prerelease', '--title', plan['title'], '--notes-file', notes)
        drafts = [r for r in api(repo, 'releases?per_page=100') if r['tag_name'] == tag and r['draft']]
        if len(drafts) != 1 or drafts[0]['target_commitish'] != sha:
            raise ValueError('Expected one draft for the tested source commit')
        draft = api(repo, f'releases/{drafts[0]["id"]}')
        expected = {p.name: p.stat().st_size for p in assets.iterdir()}
        actual = {a['name']: a['size'] for a in draft['assets'] if a['state'] == 'uploaded'}
        if actual != expected or not draft['draft']:
            raise ValueError('Draft asset verification failed; release remains unpublished')
        request = temp/'publish.json'
        request.write_text(json.dumps({'draft': False}))
        gh('api', '--method', 'PATCH', f'repos/{repo}/releases/{draft["id"]}', '--input', request)
        published = api(repo, f'releases/{draft["id"]}')
        if published['draft'] or not published['prerelease']:
            raise ValueError('Published preview status did not match')
        print(published['html_url'])


if __name__ == '__main__':
    main()
