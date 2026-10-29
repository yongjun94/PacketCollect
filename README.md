# HTTP Capture

한국어 | [English](README.en.md)

**Windows·macOS 데스크톱용 HTTP/HTTPS 로컬 캡처 및 SAZ/HAR 내보내기 도구입니다.**

> 2026-10-29 지원 범위를 데스크톱으로 한정했습니다. Android 개발·APK 배포는 중단했으며 iOS는 지원하지 않습니다. [지원 정책과 모바일 중단 사유](docs/platform-support.md)
>
> 의존성 라이선스 검토는 미완료입니다. 기술 검증용 Preview이며 일반 외부 재배포 승인과는 다릅니다. [검토 현황](docs/license-review-status.md)

## 지원 플랫폼과 다운로드

| 플랫폼 | 현재 제공 범위 |
|---|---|
| Windows x64 | Flutter 데스크톱 앱 + 번들된 Python/mitmproxy |
| macOS Apple Silicon | 같은 Flutter 앱·엔진 + macOS 프록시/Keychain 어댑터 |
| Android / iOS | 현재 개발·지원·배포 대상 아님 |

[데스크톱 Preview 다운로드](https://github.com/yongjun94/PacketCollect/releases/tag/v0.1.0-preview.20261028) · [설치 안내](release/INSTALL.md)

기존 Release에 남아 있는 Android APK는 과거 실험 산출물이며 지원 버전이 아닙니다. Windows/Mac 사용자는 ZIP을 전체 압축 해제해 실행합니다. Python·Flutter SDK를 별도로 설치할 필요가 없습니다. Windows 배포 서명과 Mac Developer ID 서명·공증은 완료되지 않았습니다.

## 개발 배경

HTTP Capture는 **Fiddler Classic의 업무·상업적 사용 라이선스 정책 변경과 유료 상용 제품인 Fiddler Everywhere로의 전환 요구에 대응하기 위해 시작한 독립 개발 프로젝트**입니다. 회사 업무와 고객 지원에 필요한 HTTP/HTTPS 수집 및 SAZ/HAR 내보내기에 집중하는 로컬 도구를 직접 구현하는 것이 목적입니다.

정확히는 Fiddler Classic 전체가 유료 제품으로 바뀐 것은 아닙니다. Progress는 2026년 8월 3일 정책 변경을 공지하고, 상업적 사용자의 전환 기한을 2026년 9월 17일로 안내했습니다. Classic은 비상업적 용도로 계속 무료 제공되며, 업무·상업적 사용에는 상용 Fiddler Everywhere로 전환하도록 안내합니다. [공식 전환 안내](https://www.telerik.com/fiddler/fiddler-classic/commercial-use) · [공식 EULA](https://www.telerik.com/purchase/license-agreement/fiddler-enterprise-support)

HTTP Capture는 Progress/Telerik의 공식 제품·포크·제휴 프로젝트가 아닙니다. SAZ 호환을 위한 자체 구현이며, 이 개발 배경이 Fiddler 라이선스의 우회나 모든 Fiddler 기능의 동등 지원을 의미하지 않습니다.

## 아키텍처와 사용 흐름

![데스크톱 아키텍처](docs/images/architecture.svg)

Windows와 Mac은 `app.dart` 화면, `desktop_engine.dart` IPC, Python/mitmproxy 엔진, `capture_core` 모델·저장소와 `capture_export` SAZ/HAR를 공유합니다. 프록시 설정과 CA 신뢰 작업만 OS 어댑터로 나뉩니다. 소스는 `http-capture/`에서 직접 수정합니다.

![데스크톱 UI 설명용 도식](docs/images/desktop-ui.svg)

Settings에서 포트·HTTPS·CA·시스템 프록시를 확인한 뒤 Start를 누릅니다. 새 요청이 세션 목록에 나타나는지 확인하고 Stop 후 SAZ/HAR로 내보냅니다. Windows에서는 시스템 프록시 적용 옵션을 확인해야 합니다. Mac은 Start에서 필요한 CA/프록시 승인을 요청합니다. UI 그림은 가상 데이터로 만든 설명용 도식입니다.

수집 대상은 **프록시를 사용하는 HTTP/HTTPS**입니다. 모든 TCP/UDP 패킷이나 모든 앱의 HTTPS 복호화를 보장하지 않습니다. CA 불신·인증서 고정·프록시 우회·기업 정책은 데스크톱에서도 제약이 됩니다. 데이터는 로컬에 저장하며 내보낸 파일에는 토큰·Cookie·개인정보가 포함될 수 있습니다.

## 개발 및 검증

- [빌드 명령](http-capture/README.md)
- [상세 아키텍처·UI](docs/architecture.ko.md)
- [코드 위치](docs/code-map.md)
- [지원 정책·검증 한계](docs/platform-support.md)
- [Windows/Mac CI](.github/workflows)

기존 Windows 버전은 사용자가 캡처 및 Fiddler Classic SAZ/Chrome DevTools HAR 가져오기를 확인했습니다. Mac은 사용자 HAR에서 Safari HTTPS 응답 저장을 확인했습니다. 플랫폼 CI 빌드·자동 테스트와 이러한 사용자 확인은 별도 증거이며 모든 앱·후속 빌드의 호환성을 뜻하지 않습니다.

모바일 소스와 과거 테스트 문서는 실험 기록으로 보존합니다. Android 자동 빌드 workflow는 실행 경로에서 옮겼고 향후 개발·배포는 Windows/Mac에 집중합니다.
