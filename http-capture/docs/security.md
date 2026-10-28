# 보안과 배포 상태

캡처 중 애플리케이션은 대상 upstream으로 원래 트래픽을 전달합니다. 로컬 처리란 추가 수집 서버/AI/동기화로 복제하지 않는다는 뜻이며 인터넷 통신 전체가 차단된다는 뜻은 아닙니다. 패키지 다운로드/감사는 개발 시에만 수행합니다. 앱 Telemetry/계정/API 업로드는 구현하지 않았습니다.

Root CA는 installation-specific confdir에서 mitmproxy가 생성합니다. 개인키를 패키지/샘플에 포함하지 않습니다. POSIX 디렉터리 0700, Windows 현재 SID ACL을 데이터 생성 전에 적용합니다. 저장 데이터와 CA는 OS 사용자 접근 제어로 보호되며 앱 수준 암호화는 없습니다. BitLocker/FileVault 등은 조직 정책에 따라 적용해야 합니다. export 파일은 사용자가 선택한 위치 권한에 따르므로 민감정보 안내 후 생성합니다. 자동 마스킹은 아직 없습니다.

CA는 사용자가 UI에서 명시적으로 설치/삭제를 선택한 뒤 실행합니다. Windows CurrentUser Root만 대상으로 사용하며, 삭제 전 로컬 CA의 SHA-256 지문을 저장소 인증서와 비교합니다. 개인키는 export하지 않습니다. 자동 만료 갱신/CA rotation은 후속 구현입니다.

프록시는 journal을 fsync한 뒤 적용하고 종료 시 restore합니다. 다른 프로그램/정책이 설정을 바꿨다면 덮어쓰지 않고 journal을 유지합니다. 비정상 종료 후 앱 시작 시 journal을 감지해 listener를 열기 전에 별도 recovery command로 자동 복원을 시도합니다. 외부 변경이 있거나 복원 실패 시 오류를 표시하고 journal을 유지합니다. 캡처 중 Settings Restore/recover도 제공합니다. CA/Proxy의 Windows API 경로는 코드만 구현, 실기 미검증입니다.

Remote capture는 아직 비활성입니다. 향후 인터페이스 선택·CIDR allowlist·세션별 임시 인증·방화벽 정책을 먼저 검증해야 합니다. 관리 정책·pinning 우회는 구현하지 않습니다.

패키지 감사 결과와 라이선스 evidence는 artifacts/와 licenses/에 기록합니다. dependency audit는 upstream advisory 매칭 결과이며 취약점의 실제 도달 가능성을 증명하지 않습니다. 남은 이슈/라이선스 누락/플랫폼 native library 검토가 해결되기 전 회사 배포 승인 완료로 간주할 수 없습니다.

앱 main()은 app.lock에 OS 파일 잠금을 유지해 같은 저장소의 중복 UI 실행을 거부합니다. Windows 실제 다중 인스턴스 시험은 미완료이며 엔진 CLI를 별도 실행하여 같은 저장소를 공유하는 사용은 지원하지 않습니다.
