# HTTP Capture — 공개용 소개

Windows·macOS 데스크톱용 HTTP/HTTPS 수집 및 SAZ/HAR 내보내기 프로젝트입니다. Fiddler Classic의 업무·상업적 이용 정책 변경에 대응해 시작한 독립 프로젝트이며 Progress/Telerik과 제휴하지 않습니다. Classic의 비상업적 무료 이용과 상업적 이용 정책은 구분합니다. [공식 안내](https://www.telerik.com/fiddler/fiddler-classic/commercial-use)

![Desktop architecture](images/architecture.svg)

Windows와 Mac은 Flutter UI, 번들된 Python/mitmproxy, 공통 Dart 세션 모델·SQLite/Body 저장·SAZ/HAR를 공유합니다. OS 프록시와 CA 신뢰는 각각 어댑터로 관리합니다. 캡처·일시정지·종료·기본 필터·요청/응답 확인·내보내기를 제공합니다.

Android 개발·APK 배포는 2026-10-29 중단했습니다. 브라우저 수집은 가능했지만 Office 앱의 HTTPS 복호화 성공을 검증하지 못해 데스크톱에 집중하기로 했습니다. iOS는 지원하지 않습니다. 이는 모든 모바일 캡처가 불가능하다는 의미가 아닙니다.

프록시를 사용하는 HTTP/HTTPS가 대상이며 모든 패킷·앱의 복호화를 보장하지 않습니다. 데이터는 로컬에 저장하고 AI·클라우드로 자동 전송하지 않습니다. 내보내기에는 민감정보가 포함될 수 있습니다.

Windows 사용자 Fiddler/DevTools 확인과 Mac 사용자 Safari HTTPS HAR 증거가 있으며 모든 앱·새 빌드의 호환성 보장은 아닙니다. mitmproxy 자체는 MIT이지만 번들 의존성 전체의 라이선스가 MIT인 것은 아닙니다. LGPL/MPL 조건·자체 코드 라이선스·배포 준수 검토와 서명/공증은 미완료입니다.

[Support policy](platform-support.md) · [Architecture](architecture.ko.md) · [Desktop UI schematic](images/desktop-ui.svg) · [License review](license-review-status.md)
