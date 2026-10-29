# 데스크톱 개발 시작 / Desktop development

현재 지원 대상은 **Windows x64와 macOS Apple Silicon**입니다. Android/iOS는 개발·배포 대상에서 제외했습니다. [정책과 배경](../docs/platform-support.md)

이 폴더가 소스 루트입니다. Flutter **3.35.5 / Dart 3.9.2**, Python **3.12.x**, mitmproxy **12.3.0**을 사용합니다. 저장소 루트에서 `cd http-capture` 후 실행합니다.

| 목적 | 명령 | 환경 |
|---|---|---|
| Windows 빌드·자동 테스트·패키징 | `python scripts/build_desktop.py windows` | Windows x64 |
| Mac 빌드·자동 테스트·패키징 | `python3.12 scripts/build_desktop.py macos` | Apple Silicon macOS |

앱만 분석할 때는 `apps/capture_app`에서 다음을 실행합니다.

```sh
flutter pub get --enforce-lockfile
flutter analyze
flutter test test/desktop
```

Exporter 테스트는 `packages/capture_export`에서 `dart pub get --enforce-lockfile`, `dart test`로 실행합니다. 전체 패키징·엔진 검증은 대상 OS의 빌드 스크립트/CI를 기준으로 합니다.

빌드 스크립트는 Python 런타임과 엔진을 번들링하므로 최종 사용자는 SDK가 필요 없습니다. 의존성 잠금 파일의 버전·해시를 임의 변경하지 마세요. 회사의 다운로드·실행 정책을 따릅니다.

Windows에서는 시스템 프록시 적용 옵션을 확인합니다. Mac은 Start에서 필요한 CA SSL 신뢰·프록시 승인을 요청합니다. Stop/정상 종료 시 앱이 관리하는 프록시 설정을 복원하고 비정상 종료 후 재실행 시 복구를 시도합니다. 강제 종료 직후 즉시 복구는 보장하지 않습니다. 기존 기업 프록시/PAC 보호 정책을 유지합니다.

[아키텍처](../docs/architecture.ko.md) · [코드 지도](../docs/code-map.md) · [설치](../release/INSTALL.md)

Android 화면·엔진·테스트·runner 생성 스크립트는 과거 실험 코드로 남아 있습니다. APK 빌드 명령과 모바일 지원을 현행 사용 흐름으로 제공하지 않습니다. Desktop is the active product; retained mobile sources are unsupported historical experiments.
