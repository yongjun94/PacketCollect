# 개발 시작

이 폴더가 프로젝트 루트입니다. Flutter 3.35.5 / Dart 3.9.2, Python 3.12.x를 기준으로 합니다. 저장소 루트에서 `cd http-capture` 후 실행합니다.

| 목적 | 명령 | 실행 환경 |
|---|---|---|
| Windows 실행판 빌드·자동 테스트 | `python scripts/build_desktop.py windows` | Windows x64 |
| Mac 실행판 빌드·자동 테스트 | `python3.12 scripts/build_desktop.py macos` | Apple Silicon macOS |
| Android runner 최초 생성 | `python3 scripts/prepare_android.py` | Flutter가 설치된 개발 환경 |
| Android 분석·단위 테스트 | `cd apps/capture_app` 후 `flutter pub get --enforce-lockfile`, `flutter analyze`, `flutter test` | Flutter/Android SDK |
| Android 개발 APK | 앱 폴더에서 `flutter build apk --debug` | Android runner 준비 후 |

데스크톱 빌드 명령은 Python 런타임과 엔진을 번들링하므로 최종 사용자는 SDK를 설치하지 않습니다. 개발 의존성 다운로드는 회사 네트워크 정책을 따릅니다. 잠금 파일의 버전/해시는 임의 변경하지 마세요. 서명·공증은 별도입니다.

`apps/capture_app/lib/main.dart`가 Android 화면과 공통 데스크톱 화면을 선택합니다. 캡처 엔진이 달라도 `packages/capture_core`와 `packages/capture_export`를 공유합니다. 상세 코드 위치는 저장소 루트의 `docs/code-map.md`를 참조하세요.

Mac은 Start에서 사용자 동의 후 CA SSL 신뢰를 준비하고 시스템 프록시를 연결합니다. Stop/정상 종료 시 설정을 복원합니다. 강제 종료 후 즉시 복구는 보장하지 않으며 재실행 시 복구를 시도합니다. 기존 기업 프록시/PAC는 덮어쓰지 않습니다. Android CA 설치는 OS의 사용자 확인 절차가 필요합니다.

이전 Windows에서 Fiddler/DevTools 가져오기를 사용자가 확인했습니다. Mac에서는 사용자 제공 HAR로 Safari HTTPS 요청·HTML 저장을 확인했습니다. Android는 이전 API35 에뮬레이터에서 검증했고 실제 기기/앱 전체 지원을 보장하지 않습니다. 이번 구조 정리는 기능 회귀 검증이 별도로 필요합니다.
