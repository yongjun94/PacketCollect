# 개발과 재현

검증 SDK: Flutter 3.35.5 (git ac4e799d237041cf905519190471f657b657155a), Dart 3.9.2, Python 3.12.14. 엔진은 mitmproxy 12.3.0으로 고정했습니다. 최초 12.2.1에서 보안 감사 후 상향했고 통합 테스트를 다시 수행합니다. 모든 Python runtime 전이 의존성은 universal 해시 lock에 기록됩니다. Flutter/Dart pubspec.lock도 포함됩니다.

Linux headless 검증:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r engines/desktop_proxy/requirements.lock
pip install pytest==9.1.1 jsonschema==4.26.0
# Dart CLI 테스트용 시스템 libsqlite3 필요 (Ubuntu: libsqlite3-dev).
(cd packages/capture_core && dart pub get --enforce-lockfile && dart analyze)
(cd packages/capture_export && dart pub get --enforce-lockfile && dart analyze && dart test)
CAPTURE_ARTIFACTS="$PWD/artifacts" python -m pytest tests -q
(cd apps/capture_app && flutter pub get --enforce-lockfile && flutter analyze && flutter test)
```

검증 환경에는 libsqlite3.so.0은 있었지만 libsqlite3.so 별칭이 없어 임시 디렉터리에 해당 시스템 라이브러리를 가리키는 별칭을 만들고 LD_LIBRARY_PATH로 지정했습니다. 실제 Flutter 앱의 Windows/macOS SQLite 배포는 sqlite3_flutter_libs가 담당합니다. 시스템 라이브러리를 배포물에 복사하지 않았습니다.

엔진 개발 실행은 `PYTHONPATH=engines/desktop_proxy/src python -m capture_proxy.main --store <private-path> --port 8877`. 표준 입력은 열린 상태로 유지하고 한 줄 JSON command를 보냅니다. EOF는 중지를 요청합니다. `HTTP_CAPTURE_PYTHON`과 `PYTHONPATH`를 설정하면 Flutter가 개발 엔진을 실행합니다. 제품 기본 경로는 실행파일 옆 `proxy/http-capture-proxy.exe`입니다.

파일 기반 raw body와 session schema는 버전 0.1입니다. DB migration/version 협상은 정식 업그레이드 배포 전 추가해야 합니다. GUI는 OS 파일 잠금으로 중복 실행을 거부하도록 구현했습니다. 별도 엔진 CLI를 같은 저장소에서 동시에 실행하는 사용은 지원하지 않습니다.

macOS 번들 스크립트는 제공하지만 sandbox entitlement, native trust/proxy adapter, 서명/공증과 실제 빌드를 완료하지 않았습니다. Android/iOS host 프로젝트는 아직 생성하지 않았습니다.

## Dart CLI native compile

```bash
cd packages/capture_export
dart compile exe bin/export_capture.dart -o http-capture-export
./http-capture-export <existing-session-store> <new-output-prefix>
```

Linux에서 실제 컴파일한 CLI로 integration store의 9개 세션을 export하는 smoke test도 통과했습니다. Windows 실행파일을 만든 것은 아닙니다. CLI 역시 sqlite3 native library가 필요합니다.
