# 데스크톱 코드 안내 / Desktop code map

현재 유지보수 대상은 Windows와 macOS입니다. [지원 정책](platform-support.md)

| 위치 (`http-capture/` 기준) | 책임 |
|---|---|
| `apps/capture_app/lib/main.dart` | 초기화·플랫폼 화면 선택. Android 분기는 과거 실험 코드 |
| `apps/capture_app/lib/app.dart` | Windows/Mac 공통 세션 목록·상세·설정·내보내기 |
| `apps/capture_app/lib/platform/desktop_engine.dart` | 번들 엔진 실행·로컬 stdio IPC |
| `packages/capture_core` | CaptureSession·SQLite·Body 파일 저장 |
| `packages/capture_export` | 공통 SAZ/HAR 생성·검증·완료 처리 |
| `engines/desktop_proxy/src/capture_proxy/main.py` | 엔진 시작·명령 분배 |
| 같은 폴더의 `proxy_addon.py`, `event_writer.py` | mitmproxy 이벤트와 Body 저장 |
| 같은 폴더의 `windows_adapter.py` | Windows 프록시·CA |
| 같은 폴더의 `macos_adapter.py`, `macos_certificate.py` | Mac 프록시·Keychain 신뢰 |
| `scripts/build_desktop.py` | Windows/Mac 빌드·검증·독립 패키징 |
| `apps/capture_app/test/desktop` | 공통 데스크톱 UI/IPC 테스트 |
| `packages/capture_export/test` 및 `tests/` | Exporter·Python 단위/통합 검증 |

SAZ/HAR 변경은 Exporter에서, 저장 필드 변경은 Core부터, OS 설정은 각 어댑터에서 수정합니다. 플랫폼별 Exporter 복사본을 만들지 않습니다. 엔진 프로토콜 변경은 Dart IPC와 Python 측을 함께 검증합니다.

## 보존한 모바일 실험

`android_app.dart`, `local_proxy_engine.dart`, `engines/android_vpn`, `test/android`, Android 관련 스크립트는 조사 기록으로 남깁니다. 현재 지원·APK 배포 대상이 아니며 일반 개발 절차로 안내하지 않습니다. Android CI와 retest 계획은 저장소 루트 `docs/archive/android-ci/`로 이동했습니다. iOS runner가 있더라도 단독 캡처 엔진 지원을 뜻하지 않습니다.

## 실행 및 검증

[빌드 명령](../http-capture/README.md)을 사용합니다. 데스크톱 Flutter 테스트 범위는 `flutter test test/desktop`입니다. 대상 OS에서 빌드 스크립트와 packaged smoke를 실행합니다. Windows/Mac CI 성공, 실제 기기 프록시·인증서 동작 및 Fiddler/DevTools Import는 각각 구분해 기록합니다. 과거 모바일 테스트 결과는 Office 앱 지원의 근거로 사용하지 않습니다.
