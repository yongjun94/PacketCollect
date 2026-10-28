# 세션 데이터

CaptureSession: id, runId, sourceDevice(IP), startTime, endTime?, request, response?, captureStatus, error?, timing, connection, tls.
HttpMessage: version, headers(원시 바이트 Base64 이름/값 목록), body?, method/url 또는 status/reason.
BodyReference: bodies/<session-id>.(request|response).bin, size, complete. 누락 null과 빈 파일 size=0은 다릅니다.

capturing event는 receiving이고, complete/error/partial/interrupted는 terminal입니다. 앱 시작 시 미완료 행은 interrupted로 변경합니다. Body가 완전히 끝난 때 fsync와 close를 수행합니다. 크래시 중 마지막 미확정 파일 부분은 회수하지 않으며 참조된 길이만 export합니다. 고아 Body 파일은 Clear 시 제거됩니다. 디스크 오류 시 무손실이나 무제한 캡처를 보장하지 않습니다.

시각은 UTC ISO8601, timing은 ms입니다. send=요청 시작~완료, wait=요청 완료~응답 시작, receive=응답 시작~완료를 관측합니다. connection DNS/connect/SSL 개별 시간은 측정하지 않으므로 HAR에서는 -1입니다. 시간 중첩(조기 응답)은 음수 duration을 만들지 않지만 정확한 클라이언트/서버별 Fiddler 타이밍으로 간주하면 안 됩니다.

HTTP/2 raw framing/HPACK/원래 pseudo-header 순서, TCP segmentation, TLS record, HTTP trailers 및 interim 1xx는 별도 원본으로 보존하지 않습니다. mitmproxy API가 제공하는 HTTP 메시지 Header/Body를 보존합니다. 모든 원본 wire byte가 보존된다는 주장을 하지 않습니다.
