# 남은 작업과 완료 조건

1. Windows x64 clean machine 빌드/실행 → Python/Flutter 없는 PC에서 bundled proxy 확인.
2. Windows CurrentUser CA install/trust/remove, 외부 인증서 불변 확인.
3. WinINet apply/normal exit/force kill/restart recover/외부 설정 변경/관리 정책/실패 rollback 검증.
4. 실제 Fiddler Classic reference SAZ 비교 및 생성 SAZ Import (URL, method,status, headers, body, binary checksum, timers, 부분 응답). 결과를 test_report에 기록.
5. 실제 Chrome DevTools Import (gzip/binary/postData 포함), 필요 시 HAR request binary/unsupported compression 정책 보완.
6. 남은 dependency vulnerability와 native OSS license 검토, target-specific SBOM/서명/설치 프로그램.
7. 수만 세션/대용량/장시간/저장소 고갈 부하, IPC backpressure/세션 보존 정책, DB migration, 다중 인스턴스 방지.
8. Brotli HAR decoding, trailers/1xx/HTTP 전 TLS 오류 connection event, UI body hex/encoding 선택 및 상세 필터.
9. macOS adapter/Keychain/프록시 복원/sandbox/서명/공증 후 실제 빌드 검증.
10. Remote Capture: explicit LAN bind, interface/CIDR allowlist/temporary auth/firewall 및 Android/iPhone 실기 연결.
11. Android: 네트워크 stack/엔진 라이선스 검토 → VpnService TCP forwarding → HTTP → permitted TLS → 공통 adapter. 사용자 CA/pinning 제약 유지.
12. iOS: entitlement/배포 가능성 검증 → PacketTunnel proof → 앱 범위/TLS 한계 → adapter.

Phase 1은 자동 형식 검증 경로가 구현됐습니다. 실제 reference SAZ를 확보하지 못해 sample comparison은 남아 있습니다. Phase 2는 실행 가능한 소스와 Windows build recipe까지 구현했지만 Windows acceptance 목표를 달성했다고 표시하지 않습니다. 이후 Phase는 인터페이스/설계만 제공합니다.
