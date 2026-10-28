# 아키텍처

Flutter UI → `CaptureEngine` 인터페이스 → DesktopEngine → 상속 stdio 파이프 → Python mitmproxy. Python은 Body를 전용 디렉터리에 스트리밍 저장하고, 표준 session snapshot JSON을 전송합니다. Dart Capture Core만 SQLite에 메타데이터를 기록합니다. Capture Export는 엔진/UI를 참조하지 않습니다.

프로세스 분리로 엔진 중단이 UI 프로세스의 직접 크래시로 이어지지 않습니다. Export는 캡처를 멈춘 후 별도 Dart isolate에서 수행합니다. SQLite WAL/FULL 및 엔진 Body fsync로 terminal event 이전의 Body 저장을 완료합니다. 갑작스러운 OS/디스크 오류에 대한 무손실 보장은 하지 않습니다.

Header는 이름/값 원시 바이트 쌍의 Base64 목록입니다. Python에서 dict로 합치지 않습니다. Body는 HTTP transfer framing을 제거한 raw entity bytes입니다. gzip/Brotli 압축은 저장 시 풀지 않습니다. 이는 TCP 패킷 캡처 또는 wire byte 재현이 아닙니다.

UI는 100개씩 DB 페이지를 읽고 ListView.builder를 사용합니다. 최근 13개 이하 페이지를 유지합니다. UI 알림은 250ms 간격으로 합칩니다. 수만 세션/장시간 부하 성능은 미측정입니다.

모바일에서는 native tunnel이 TCP/IP 스택과 HTTP/TLS 프록시를 별도로 구현해야 합니다. VpnService/PacketTunnel은 복호화 엔진이 아닙니다. 동일 session JSON/BodyReference로 adapter를 만들면 Core/Export를 재사용할 수 있습니다. 미구현 native 엔진에 가짜 구현은 제공하지 않습니다.

현재 기술 스택은 유지했습니다. IPC는 네트워크 인증 포트보다 배포·접근 제한이 간단한 상속 파이프를 선택했습니다. Windows system proxy/CA adapter는 엔진 패키지 안 별도 Python 모듈이며 Flutter는 command만 호출합니다. 추후 네이티브 adapter로 교체해도 session/export 모델은 영향을 받지 않습니다.
