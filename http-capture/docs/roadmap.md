# 데스크톱 후속 개발

2026-10-29부터 Windows x64 / macOS Apple Silicon에 집중합니다. Android 실험과 APK 배포를 중단하고 iOS·모바일 원격 캡처를 현재 로드맵에서 제외합니다. [지원 정책](../../docs/platform-support.md)

1. Windows/Mac clean machine 설치·실행, CA 설치/신뢰/제거와 프록시 정상 종료·비정상 종료 복구 검증.
2. Fiddler Classic SAZ 및 Chrome DevTools HAR 호환성 회귀 확인. 기존 Windows 사용자 확인과 새 빌드 검증을 구분.
3. 수만 세션·장시간·대용량·저장소 고갈 부하 측정, IPC backpressure, 보존 정책과 DB migration.
4. Body 표시·압축 인코딩 처리·부분 수집 상태·기본 필터 개선.
5. 플랫폼별 SBOM·고지·의존성 소스 제공/재결합 조건 등 라이선스 검토.
6. Windows 배포 서명, Mac Developer ID 서명·공증 및 설치 패키지·업데이트 정책.

구현·자동 테스트·실기기·외부 Import 검증을 따로 기록합니다. 측정하지 않은 성능이나 검증하지 않은 앱 호환성을 완료로 표시하지 않습니다.
