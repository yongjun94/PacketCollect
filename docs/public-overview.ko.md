# HTTP Capture — 공개용 프로젝트 소개

> 이 문서는 공개 소개에 사용할 수 있도록 정리한 초안입니다. 저장소 공개 전환, 자체 코드의 라이선스 부여 또는 실행 파일의 라이선스 검토 완료를 의미하지 않습니다.

## 프로젝트 소개

HTTP Capture는 Windows, macOS, Android에서 프록시를 사용하는 HTTP/HTTPS 요청·응답을 로컬에 수집하고 SAZ/HAR 파일로 내보내는 독립 개발 프로젝트입니다. 네트워크 문제 해결에 필요한 세션 기록과 파일 생성에 집중합니다.

개발 계기는 Fiddler Classic의 업무·상업적 사용 라이선스 정책 변경입니다. Progress가 해당 사용자에게 상용 Fiddler Everywhere로 전환하도록 안내하면서, 업무에 필요한 기본 캡처·내보내기 흐름을 독립적으로 구현하기 시작했습니다. Fiddler Classic은 비상업적 용도로 계속 무료 제공됩니다. [공식 안내](https://www.telerik.com/fiddler/fiddler-classic/commercial-use)

이 프로젝트는 Progress/Telerik과 제휴하지 않으며 Fiddler의 공식 배포판이 아닙니다.

## 전체 구조

![플랫폼별 수집과 공통 모듈](images/architecture.svg)

| 영역 | 역할 |
|---|---|
| Flutter UI | 데스크톱 세션 목록·상세 보기와 Android VPN/인증서 사용자 흐름 |
| 데스크톱 엔진 | 번들된 Python/mitmproxy를 통한 HTTP/HTTPS 프록시 수집 |
| Android 엔진 | Dart 로컬 프록시와 Kotlin VPN·CA 연동 |
| Capture Core | 공통 세션 모델, SQLite 메타데이터, 별도 Body 파일 |
| Capture Export | 같은 Dart 코드로 SAZ/HAR 생성 |

Windows와 Mac은 데스크톱 화면과 엔진을 공유하고 OS별 프록시·인증서 adapter를 사용합니다. Android는 별도 화면과 엔진을 사용하면서 공통 모델·저장·Exporter를 재사용합니다.

## 제공하는 기능

- HTTP/HTTPS 요청·응답, Header, Body 및 수집 상태 기록
- 사용자 동의를 거친 로컬 CA 관리와 지원 가능한 HTTPS 복호화
- 세션 목록, 기본 문자열 필터, 요청·응답 확인
- SAZ 및 HAR 내보내기
- 관리 중인 프록시 설정의 중지·종료 처리와 복구 경로

[데스크톱 UI 안내](images/desktop-ui.svg) · [Android UI 안내](images/android-ui.svg)

그림은 현재 코드에 근거한 설명용 도식이며 데이터는 가상 예시입니다. 고객 트래픽이나 실제 사용자 화면을 공개한 것이 아닙니다.

## 지원 범위와 검증

현재 배포 대상은 Windows x64, Apple Silicon Mac, Android입니다. 공통 소스 정리 후 세 플랫폼의 빌드·자동 테스트가 통과했고 Android API35 에뮬레이터에서 HTTP/HTTPS와 캡처 종료 시 VPN 프록시 해제를 확인했습니다. 이전 Windows 버전은 사용자가 Fiddler/DevTools 가져오기를 확인했고, Mac 사용자 HAR에서도 Safari HTTPS 응답 저장을 확인했습니다. 모든 새 빌드·실기기·앱을 검증한 것은 아닙니다.

이 도구는 모든 TCP/UDP 패킷을 수집하는 프로그램이 아닙니다. 프록시를 무시하는 앱, 사용자 CA 불신, 인증서 고정, bypass 규칙과 기업 네트워크 정책에 따라 수집이 제한됩니다. 현재 Android VPN은 HTTP 프록시 힌트를 제공하며 일반 패킷 처리 스택이 아닙니다. iOS 단독 캡처·HTTP/3·WebSocket payload·원격 캡처 UI는 현재 제공 범위가 아닙니다.

## 데이터와 라이선스 상태

수집 데이터는 로컬에 저장하며 AI 분석 서비스나 클라우드 동기화로 자동 전송하지 않습니다. 사용자가 선택한 내보내기 위치는 외부 저장소일 수 있습니다. 캡처에는 토큰·Cookie·개인정보가 포함될 수 있으며 자동 마스킹은 구현되지 않았습니다.

mitmproxy 자체는 MIT이지만 배포물 전체가 MIT인 것은 아닙니다. 데스크톱 번들에는 LGPL/MPL 등 별도 조건을 가진 의존성이 포함되어 있습니다. 라이선스 고지·SBOM은 검토 증거이며 배포 승인서가 아닙니다. 자체 코드의 최상위 라이선스와 의존성 소스 제공·재결합 조건은 검토 중입니다. 현재 실행 파일은 기술 검증용 Preview이며 일반 외부 재배포가 승인된 패키지로 취급하지 않습니다.

[라이선스 검토 현황](license-review-status.md) · [공개 전 확인 목록](publication-checklist.md) · [상세 아키텍처](architecture.ko.md)
