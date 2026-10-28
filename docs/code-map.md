# 코드 안내와 유지보수 규칙

## 폴더 역할

| 위치 (`http-capture/` 기준) | 책임 | 공유 범위 |
|---|---|---|
| `apps/capture_app/lib/main.dart` | 저장소 초기화와 화면 선택 | 전체 |
| `apps/capture_app/lib/app.dart` | 세션 목록·설정·내보내기 데스크톱 화면 | Windows / Mac |
| `apps/capture_app/lib/android_app.dart` | Android 화면·VPN/CA 사용자 흐름 | Android |
| `apps/capture_app/lib/platform/desktop_engine.dart` | Python 엔진 실행·로컬 stdio 명령 | Windows / Mac |
| `apps/capture_app/lib/platform/local_proxy_engine.dart` | Android 로컬 HTTP/TLS 프록시 | Android |
| `packages/capture_core` | 세션 모델·SQLite·Body 파일 저장 | 전체 |
| `packages/capture_export` | SAZ/HAR 생성·검증 | 전체 |
| `engines/desktop_proxy/src/capture_proxy/proxy_addon.py` | mitmproxy 이벤트 → 공통 모델 | Windows / Mac |
| `engines/desktop_proxy/src/capture_proxy/main.py` | 엔진 시작과 명령 분배 | Windows / Mac |
| 같은 폴더의 `windows_adapter.py` | Windows 프록시·CA 저장소 | Windows |
| 같은 폴더의 `macos_adapter.py`, `macos_certificate.py` | Mac 프록시·CA 신뢰 | Mac |
| `engines/android_vpn` | Kotlin 서비스·Android CA·Manifest | Android |
| `scripts/build_desktop.py` | 공통 데스크톱 빌드·패키징 | Windows / Mac |
| `scripts/prepare_android.py` | Flutter runner 생성과 네이티브 엔진 연결 | Android |
| `tests` 및 각 Dart 패키지의 `test` | 자동 검증 | 테스트별 |

## 어디를 수정하나요?

- SAZ/HAR 형식: `packages/capture_export`. UI나 OS별 복사본을 만들지 않습니다.
- 저장 필드: `capture_core` 모델을 먼저 변경한 후 Python/Dart 엔진 이벤트 어댑터와 Exporter를 함께 검증합니다.
- 데스크톱 화면: `app.dart` 한 곳. OS별 인증서·프록시 작업은 엔진 명령으로 호출합니다.
- Android 네이티브: `engines/android_vpn` 수정 후 생성된 `apps/capture_app/android/`를 삭제하고 `prepare_android.py`를 다시 실행합니다. 생성 디렉터리를 원본으로 수정하지 않습니다.
- Python 버전·패키지: 잠금 파일과 라이선스/SBOM 검증을 함께 갱신합니다.

## 구조 정리 범위

기존 ZIP에서 공통 소스를 추출하고 최신 수정본을 적용해 실제 파일로 추적합니다. Windows와 Mac은 기존 Mac 수정본에 포함된 Windows 분기를 사용해 UI·엔진·빌드 스크립트를 공유합니다. Android Dart 코드는 같은 앱 폴더에서 런타임 분기로 선택합니다. 플랫폼 엔진까지 하나로 합친 것은 아닙니다.

Android runner는 고정 Flutter SDK로 생성하며 Dart 소스를 덮어쓰지 않습니다. 완전한 Android Gradle runner 체크인은 후속 정리 범위입니다. iOS runner가 있어도 독립 캡처 엔진은 구현되지 않았습니다.

## 검증 해석

기존 버전: Windows 사용자 캡처/Fiddler/DevTools 확인, Mac 사용자 HAR에서 Safari HTTPS 200/HTML 확인, Android API35 에뮬레이터 확인. 구조 변경 후에는 새 CI 결과가 기준입니다. 빌드 성공과 OS 설정 변경·실제 브라우저 동작 확인을 구분합니다. 기업 PAC/upstream, 인증서 고정, 모든 앱/패킷 수집, 배포 서명·공증은 완료로 취급하지 않습니다.

`http-capture/docs` 안의 초기 설계·이전 테스트 보고서는 역사적 문서입니다. 현재 구현 위치는 이 문서와 실제 소스/CI를 우선합니다.

### 테스트 실행 범위

데스크톱 UI·IPC는 `apps/capture_app/test/desktop`, Android UI·Dart HTTP/TLS 엔진은 `test/android`에 있습니다. 데스크톱 빌드는 `flutter test test/desktop`, Android Linux CI는 `flutter test test/android test/desktop`을 실행합니다. Android용 Dart TLS fixture는 Mac의 네이티브 신뢰 검증 차이로 실패했으며 Mac 엔진 지원으로 간주하지 않습니다. Mac의 실제 Python/mitmproxy 엔진은 별도 packaged smoke와 실기기 검증 대상입니다. 테스트 자체를 삭제하거나 TLS 검증을 완화하지 않습니다.
