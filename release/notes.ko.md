# HTTP Capture — Windows / macOS 데스크톱 Preview

**2026-10-29부터 Windows·macOS만 개발·지원·배포합니다.** Android 실험 개발과 APK 배포는 중단했으며 iOS는 지원하지 않습니다. 기존 Assets에 APK가 남아 있다면 과거 실험 산출물이며 지원 버전이 아닙니다. 첨부된 예전 설치 문서보다 아래 저장소의 최신 설치 안내를 우선하세요.

| 파일 | 대상 |
|---|---|
| HTTP-Capture-Windows-x64.zip | Windows x64 |
| HTTP-Capture-macOS-arm64.zip | macOS Apple Silicon |

[최신 설치 안내](https://github.com/yongjun94/PacketCollect/blob/main/release/INSTALL.md) · [지원 범위·모바일 중단 이유](https://github.com/yongjun94/PacketCollect/blob/main/docs/platform-support.md) · [아키텍처·UI](https://github.com/yongjun94/PacketCollect/blob/main/docs/architecture.ko.md)

Android 브라우저 수집은 가능했지만 Office 앱의 HTTPS 복호화 성공을 검증하지 못해 데스크톱에 집중합니다. 모든 모바일 캡처가 불가능하거나 데스크톱의 모든 앱이 복호화된다는 의미는 아닙니다.

Fiddler Classic의 업무·상업적 이용 정책 변경에 대응해 시작한 독립 프로젝트이며 Progress/Telerik과 제휴하지 않습니다. Classic 비상업적 이용은 계속 무료라는 점을 구분합니다.

Windows/Mac 파일은 기존에 성공한 동일 소스 CI 빌드의 산출물입니다. Windows 사용자 Fiddler/DevTools 확인과 Mac 사용자 Safari HTTPS HAR 증거는 모든 앱·후속 빌드의 검증을 뜻하지 않습니다. 소스 커밋: `{{SOURCE_SHA}}`.

Python·Flutter SDK는 최종 사용자에게 필요 없습니다. Windows 배포 서명, Mac Developer ID 서명·공증은 미완료입니다. 조직의 실행·설치 정책을 따르세요. 모든 패킷이 아닌 프록시를 따르는 HTTP/HTTPS가 대상입니다. 캡처 파일에는 민감정보가 포함될 수 있습니다.

SHA256SUMS.txt와 build-provenance.json은 기존 파일의 무결성·CI 출처 확인용입니다. 바이너리나 기존 체크섬은 이번 지원 정책 변경으로 재작성하지 않습니다. 의존성 라이선스 검토는 별도 미완료 항목입니다.
