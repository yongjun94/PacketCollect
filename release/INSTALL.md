# HTTP Capture Preview 설치 안내

개발용 사전 배포입니다. Windows x64, macOS Apple Silicon, Android용이며 iOS와 Intel Mac 실행판은 포함하지 않습니다. Python/Flutter SDK를 최종 사용자 PC에 별도로 설치할 필요가 없습니다.

## Windows

HTTP-Capture-Windows-x64.zip을 새 폴더에 전체 압축 해제하고 그 안의 HTTP-Capture.exe를 실행합니다. DLL/proxy/resources 폴더도 함께 있어야 합니다. HTTPS 복호화는 앱 설정에서 해당 설치본의 CA를 사용자 동의 후 설치합니다. 회사 보안 정책에 따라 배포 서명이 없는 실행 파일이 차단될 수 있습니다. 보안 정책을 우회하지 마세요.

## macOS Apple Silicon

HTTP-Capture-macOS-arm64.zip을 압축 해제해 HTTP-Capture.app을 Applications로 복사합니다. Start에서 CA SSL 신뢰와 시스템 프록시 적용을 승인합니다. 설정에서 CA 상태를 확인할 수 있습니다. 이 앱은 ad-hoc 서명만 있고 Developer ID 서명·Apple 공증은 없습니다. Gatekeeper/회사 정책에 따라 실행이 거부될 수 있으며, 실행 허용 여부는 조직 정책을 따릅니다. 강제 종료 직후 프록시 자동 복구는 보장하지 않으며 재실행 시 복구를 시도합니다.

## Android

HTTP-Capture-Android-preview.apk을 기기에 다운로드하고 Android가 요청하는 해당 설치 앱의 APK 설치 권한을 확인한 뒤 설치합니다. VPN 사용 승인이 필요합니다. HTTPS CA는 앱 안내에 따라 공개 인증서만 시스템 설정에서 사용자 확인 후 설치합니다. 앱 ID는 dev.httpcapture.capture_app.all입니다. 이 APK는 개발용 debug 서명이며 이전 APK와 서명 키가 다르면 덮어쓰기 설치가 거부될 수 있습니다. 기존 데이터를 내보내기 전에는 기존 앱을 삭제하지 마세요. 안정적인 업데이트 서명 키 관리는 후속 배포 범위입니다.

## 검증과 범위

세 파일은 같은 소스 커밋의 성공한 CI 빌드에서 가져왔습니다. Windows/Mac 빌드·자동 테스트 및 Android API35 에뮬레이터 HTTP/HTTPS, 중지/종료 후 프록시 해제 검증을 통과했습니다. 모든 실제 기기·앱에서의 동작과 사용자 CA 설치 절차를 검증한 것은 아닙니다. 시스템 프록시를 따르는 HTTP/HTTPS가 대상이며 전체 TCP/UDP 패킷 캡처, 인증서 고정 우회, iOS 단독 캡처는 제공하지 않습니다.

캡처/내보낸 파일에는 쿠키·토큰·고객 데이터가 포함될 수 있습니다. 공개 배포 파일에는 사용자 트래픽이나 공통 CA 개인키를 포함하지 않습니다. SHA256SUMS.txt는 전송된 파일의 무결성 확인용이며 코드 서명을 대신하지 않습니다.
