# 엔진 프로토콜

기본 listen=127.0.0.1, port=8877. Remote bind 인자는 없습니다. `--no-decrypt`는 CONNECT pass-through이며 해당 HTTPS의 HTTP 세션은 기록되지 않습니다. HTTP/2는 실제 ALPN h2 end-to-end 테스트를 수행했습니다. HTTP/3, WebSocket frame은 지원 범위 밖입니다.

NDJSON stdout 이벤트: ca(path, SHA256 fingerprint), ready(port,pid,recoveryNeeded), session(session snapshot), ack(id,result), command_error(id,error), stopped, fatal, recovery_error. stderr는 UI에서 버리고 원시 트래픽을 별도 로그 파일에 쓰지 않습니다.

stdin command: {id,action,...}. action=pause(paused), stop, proxy_enable, proxy_restore, certificate_status, certificate_install(consent:true), certificate_remove(consent:true). 앱은 최대 20초 응답 대기 후 실패를 표시합니다. listener 설치 후 ready가 발생합니다. stdin EOF는 shutdown입니다. 별도 --recover-proxy 명령은 listener/CA 생성 없이 journal 복원을 수행하고 종료합니다.

플랫폼 기능 실패는 실제 command_error입니다. Linux/macOS에서 Windows CA/proxy command가 성공한 것처럼 처리하지 않습니다. Windows 프록시는 HKCU WinINet의 ProxyEnable/Server/Override만 변경합니다. WinHTTP, VPN connection, 브라우저 독립 설정과 PAC/WPAD 환경을 자동으로 처리하지 않습니다.

pinning, 사용자 CA 미신뢰, 프록시를 무시하는 앱은 복호화를 보장하지 않습니다. TLS 핸드셰이크에서 HTTP 이전에 실패하면 HTTP 세션이 존재하지 않을 수 있습니다. 현재 UI는 이러한 모든 연결 실패를 개별 세션으로 표시하지 못합니다. 별도 connection event 확장이 필요합니다.
