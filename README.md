# HTTP Capture

Windows, macOS, Android용 로컬 HTTP 캡처 실험 프로젝트입니다. 모든 운영체제에서 같은 완제품이 제공되는 것은 아닙니다. 현재 GitHub는 **공통 소스 ZIP + 플랫폼별 덮어쓰기(overlay)** 형태이며, README 아래의 절차로 빌드 가능한 폴더를 생성할 수 있습니다.

## 현재 플랫폼과 공유 범위

| 영역 | Windows | macOS | Android |
| --- | --- | --- | --- |
| 공통 데이터 모델·SQLite·파일 저장 | `packages/capture_core` | 동일 공통 패키지 | 동일 공통 패키지 |
| SAZ/HAR 출력 | `packages/capture_export` | 동일 공통 패키지 | 동일 공통 패키지 |
| UI | `fixes/.../app.dart` 데스크톱 UI | `macos-fixes/.../app.dart` 별도 수정본 | `android-fixes/.../android_app.dart` 별도 UI |
| 캡처 엔진 | Python/mitmproxy 별도 프로세스 | Python/mitmproxy 별도 프로세스 | Dart 로컬 프록시 + Kotlin VPN/CA |
| OS 설정 | WinINet/CurrentUser CA | Start에서 시스템 HTTP/HTTPS 프록시 자동 적용·Stop에서 복원. CA 설치·현재 사용자 SSL 신뢰·삭제는 앱에서 동의 후 진행 | VPN 단위 프록시. CA 설치는 Android 시스템 절차 |
| 검증 | 사용자가 Windows 캡처와 Fiddler SAZ/DevTools HAR 가져오기 확인 | Apple Silicon 빌드·자동 테스트 통과, 사용자 curl HTTP 캡처 확인. 새 자동 프록시·브라우저 HTTPS는 실기기 미검증 | API35 에뮬레이터 검증. 실기기 HTTPS/CA 설치 미검증 |

Android는 프록시를 사용하는 앱만 지원하며 전체 TCP/UDP 패킷 캡처 엔진이 아닙니다. 사용자 CA를 신뢰하지 않는 앱, 인증서 고정, HTTP/3는 복호화되지 않을 수 있습니다. iOS 독립 캡처는 구현되지 않았습니다.

## GitHub 폴더가 여러 코드로 보이는 이유

- `HTTP-Capture-Source.zip`: 공통 모델·스토어·Exporter와 데스크톱 원본 프로젝트.
- `fixes/`: Windows 데스크톱에 적용하는 수정본. macOS와 Android 빌드에서도 먼저 복사합니다.
- `macos-fixes/`: macOS 빌드에서 `fixes` 위에 적용하는 수정본.
- `android-fixes/`, `android-native/`: Android 빌드에 적용하는 Dart UI/프록시와 Kotlin Activity/VPN/인증서 코드.
- `build_desktop.py`: Windows 빌드 스크립트. macOS는 `macos-fixes/scripts/build_desktop.py`가 이를 대체합니다.
- `.github/workflows/`: 각 플랫폼별로 위 파일을 조립하고 빌드/테스트하는 실제 절차.

이 구조는 현재 코드 중복과 덮어쓰기 순서에 의존하는 **전환기 구조**입니다. 하나의 공통 UI가 Windows/macOS/Android에서 그대로 실행되는 상태는 아닙니다. 원본 ZIP 내부의 오래된 README/테스트 보고서는 최신 플랫폼 상태를 반영하지 않을 수 있습니다. 추후 실제 단일 monorepo로 정리할 때는 각 플랫폼 빌드의 결과를 비교하고 별도 검증해야 합니다.

## 소스 폴더 만들기

저장소 ZIP 다운로드 후 압축을 풀고, `HTTP-Capture-Source.zip`, `fixes`, `macos-fixes`, `android-fixes`가 보이는 폴더에서 실행합니다. `--output`은 **존재하지 않는 새 폴더**여야 합니다.

```sh
python3 scripts/materialize.py macos --output ../http-capture-macos
python3 scripts/materialize.py android --generate-android --output ../http-capture-android
```

Windows PowerShell에서는 `python scripts/materialize.py windows --output ../http-capture-windows`를 사용합니다. Android는 Flutter가 PATH에 있어야 하며 해당 플랫폼 runner를 새로 생성합니다. 각 출력 폴더의 `packages/`는 같은 공통 소스를 사용하고, 앱 및 OS 코드는 플랫폼별로 선택됩니다. 이 명령은 설치 패키지를 빌드하거나 서명하지 않습니다. 기존 GitHub Actions도 아직 개별 overlay를 사용하므로 코드 변경 시 동기화가 필요합니다.

## macOS 자동 캡처 사용

최신 Apple Silicon preview는 Start에서 시스템 HTTP/HTTPS 프록시를 연결합니다. macOS 관리자 승인이 필요할 수 있습니다. 기존 프록시/PAC/자동 검색을 발견하면 변경을 거부합니다. Stop·정상 종료 시 원래 설정을 복원합니다. 강제 종료·전원 손실 직후 복원은 보장되지 않으며 재실행 또는 Settings의 Restore / recover로 복구합니다. HTTPS 캡처 시작 전 CA 신뢰를 확인하고, 필요하면 동의 후 현재 사용자 키체인에 공개 CA를 설치하고 SSL 신뢰를 설정합니다. Settings에서 설치·신뢰 확인·앱이 설치한 CA 삭제를 할 수 있습니다. 기존에 수동 설치한 미관리 인증서는 자동 변경하지 않습니다. 자세한 절차는 `macos-fixes/docs/macos-ca-trust.md`를 참조하세요. 모든 패킷이 아니라 시스템 프록시를 따르는 HTTP/HTTPS가 대상이며 기존 bypass 목록도 유지됩니다.

빌드 [40611423214](https://github.com/yongjun94/PacketCollect/actions/runs/40611423214): arm64 빌드, Flutter analyze, UI 4건, exporter 7건, 프록시 mock 테스트 4건 및 내장 엔진 smoke 통과. 실제 관리자 승인·브라우저 HTTPS·강제 종료 후 복원은 미검증입니다.

## 기업 네트워크와 보안

Windows 자동 시스템 프록시 전환은 **기존에 활성화된 명시적 프록시**나 PAC URL을 발견하면 변경하지 않고 오류를 반환합니다. 복원은 앱이 수정한 항목만 다루며, 외부에서 변경한 PAC URL은 그대로 둡니다. 기존 프록시를 upstream으로 연결하는 기능은 아직 없습니다. 이 확인은 WPAD 자동 검색, VPN별 연결, WinHTTP, 그룹 정책을 전부 판단하지 못하므로 기업 프록시 호환성이 보장되는 것은 아닙니다. 회사 정책에 따른 테스트 환경에서 먼저 확인하세요.

CA 설치는 사용자 동의가 필요합니다. 캡처와 내보낸 파일에는 토큰·쿠키·고객 정보가 들어갈 수 있으며, 현재 자동 마스킹은 구현되지 않았습니다. SAZ/HAR의 기능이나 데이터 보존을 변경하는 옵션을 기본으로 켜지 않습니다. 실기기별 검증, 배포용 서명, 의존성 보안 및 라이선스 검토는 별도입니다.

## 개선 우선순위

1. **진행:** 공유 코드와 플랫폼별 오버레이를 재현·검증하기 쉽게 구성하고, 기존 프록시 덮어쓰기 방지.
2. PAC/WPAD/VPN별 프록시 상태 확인과 정책을 지키는 upstream 설계 및 Windows 실제 환경 검증.
3. NTLM/Negotiate 등 연결 단위 인증을 합성 테스트와 실제 도메인에서 검증.
4. 원본 보존 또는 선택적 민감정보 마스킹을 명확히 선택하고, SAZ/HAR 전체 필드·본문·메타데이터의 누출 및 호환성 테스트.
5. macOS/Android 실기기 검증과 공통 UI·플랫폼 어댑터 통합. WebSocket·iOS는 별도 범위로 진행.

CA 관리 빌드 [40612696093](https://github.com/yongjun94/PacketCollect/actions/runs/40612696093): 기존 UI/Exporter 테스트와 인증서 동의·소유권 mock 테스트 5건 통과. macOS 실제 승인 UI와 Safari HTTPS는 아직 실기기 확인이 필요합니다.
