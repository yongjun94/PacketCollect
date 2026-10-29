# 지원 정책 / Platform support

정책 변경일 / Effective: **2026-10-29**

## 현재 범위 / Current scope

| 플랫폼 / Platform | 상태 / Status |
|---|---|
| Windows x64 | 개발·유지보수·Preview 배포 / Active |
| macOS Apple Silicon | 개발·유지보수·Preview 배포 / Active |
| Intel Mac | 실행 패키지 미제공 / No supplied package |
| Android | 실험 개발 및 APK 배포 중단 / Discontinued experiment |
| iOS | 미구현·현재 로드맵 제외 / Unimplemented, outside roadmap |
| 모바일 → PC 원격 캡처 | 현재 구현·지원 범위 아님 / Not currently implemented or supported |

## 모바일 개발을 중단한 이유

Android 브라우저 HTTPS 수집은 동작했지만 사용자 기기의 Excel·Copilot 테스트에서 클라이언트 측 TLS 인증서 거부가 계속 발생했습니다. 제공된 HAR에는 `client-tls-handshake` 단계의 `SSLV3_ALERT_CERTIFICATE_UNKNOWN`이 기록됐습니다. 복호화를 끄면 앱 연결은 복구되지만 HTTPS 헤더·Body는 얻을 수 없었습니다.

CA/서버 인증서 SKI·AKI 보완, 인증서 체인·호스트 검증 및 에뮬레이터 테스트를 수행했지만 실제 Office 앱의 복호화 성공은 확인하지 못했습니다. 이 오류만으로 certificate pinning을 확정하지 않습니다. 앱이 사용자 CA를 신뢰하지 않는 등 원인을 구분하려면 해당 앱의 공식 진단·개발 지원이 필요합니다. HTTP Capture 설정으로 다른 앱의 신뢰 정책을 강제 변경하지 않습니다.

따라서 업무 목표인 Office HTTPS 자료 수집을 모바일에서 안정적으로 제공할 수 없다고 판단해 **제품 범위를 데스크톱으로 한정**합니다. 이는 모든 모바일 트래픽 캡처가 기술적으로 불가능하다는 뜻이 아닙니다. 데스크톱에서도 모든 앱의 복호화를 보장하지 않습니다.

## Why mobile was discontinued

Browser HTTPS capture worked, but the user's Excel/Copilot tests continued to reject interception certificates during client-facing TLS. Disabling decryption restored connectivity while leaving HTTPS headers/bodies encrypted. Certificate-profile improvements and emulator checks did not demonstrate successful Office decryption. The alert alone does not prove certificate pinning.

We therefore limit the product to desktop capture rather than claim reliable mobile Office HTTPS support. This is a project scope decision, not a claim that all mobile capture is impossible. Desktop interception also remains subject to application trust and proxy policies.

## 소스·CI·기존 배포 처리 / Source, CI and releases

- 모바일 소스와 테스트는 조사 기록으로 보존하며 지원 기능으로 취급하지 않습니다.
- Android workflow와 retest 계획은 `docs/archive/android-ci/`로 이동해 자동/수동 Actions 실행 목록에서 제외합니다.
- 새 배포 검증은 Windows·macOS 두 플랫폼을 요구하며 Android를 거부합니다.
- 기존 Release 바이너리와 체크섬은 재작성하지 않습니다. 남아 있는 APK 및 첨부 설치 문서는 과거 산출물입니다. 현재 사용 안내는 저장소의 `release/INSTALL.md`와 `INSTALL.en.md`가 기준입니다.
- Mobile code/tests remain historical; archived CI is inactive. New releases require Windows and macOS only. Existing release assets/checksums remain unchanged and historical APKs are unsupported.

## 검증 기준 / Evidence

Windows 캡처 및 Fiddler/DevTools 가져오기는 사용자가 기존 버전에서 확인했습니다. Mac Safari HTTPS 응답도 사용자 HAR로 확인했습니다. CI 성공, 실제 기기 실행, 외부 앱 호환성은 각각 구분합니다. 이번 지원 정책 변경은 런타임 캡처 코드를 변경하지 않습니다. 라이선스 검토·배포 서명·Mac 공증은 별도 미완료 항목입니다.

## 배포 관리 / Release management

`release/preview.json`은 다음 수동 배포 후보 계획입니다. 자동 게시는 하지 않으며 Publish tested desktop preview downloads를 수동 실행할 때 같은 소스의 성공한 Windows/Mac CI·아티팩트를 다시 검증합니다. 기존 2026-10-28 3플랫폼 계획은 `release/archive/preview.20261028.json`에 보존했습니다. 배포 계획 변경 자체는 새 바이너리 빌드·실기기 검증이 아닙니다.
