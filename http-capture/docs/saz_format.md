# SAZ와 HAR 표현

SAZ: `[Content_Types].xml` + raw/{n}_c.txt, 응답이 있으면 {n}_s.txt, {n}_m.xml. Streaming ZIP STORE/data descriptor/CRC32 방식으로 Body 전체를 RAM에 올리지 않습니다. ZIP64는 아직 없으며 4GiB archive/entry 한계 또는 65535 ZIP member 한계 전에 오류와 임시파일 삭제로 끝냅니다. 압축률보다 재현성과 메모리 제한을 우선했습니다.

HTTP/1 헤더-본문은 CRLF/CRLF로 구분하며 Body 바이트는 그대로 기록합니다. mitmproxy가 제거한 chunk framing과 일치하도록 Transfer-Encoding/Trailer를 제거하고 실제 저장 길이의 Content-Length를 씁니다. 기존 헤더는 session flags에 Base64 JSON으로 보존합니다. 중복 헤더와 순서는 framing 정규화 대상을 제외하고 유지됩니다. HTTP/2 start line은 HTTP/1.1로 변환하며 원래 버전을 XML flag에 기록합니다. HTTPS Session BitFlags는 IsHTTPS=1입니다. 미수집 응답을 502 등으로 만들지 않습니다.

Metadata에는 SID/SessionTimers/SessionFlags와 앱의 원본 session id/run/status/error를 넣습니다. 관측한 begin/end만 사용합니다. Fiddler XML의 모든 시간/플래그를 추정해서 채우지 않습니다.

**실제 Fiddler Classic 저장 파일과 비교 및 Fiddler Import는 미완료입니다.** 현재 자동 검증은 자체 생성 테스트 데이터의 ZIP CRC/형식/XML/원본 Body 비교입니다. `scripts/compare_saz.py`로 실제 Fiddler reference를 비교할 수 있습니다. 응답 없는 세션의 Fiddler 로딩 동작도 반드시 확인해야 합니다. 구조 검증을 Fiddler 호환성 보증으로 해석하지 마세요.

HAR 1.2: cookies/queryString/postData/content/cache/timings 포함. binary response content.text는 Base64입니다. gzip은 decoded content를 스트리밍으로 생성하고 원래 압축 bytes도 _httpCaptureRawContent에 보존합니다. Brotli 등 미지원 decoding이나 gzip 손상/부분 수집은 표준 content.text를 생략하고 extension에 raw Base64를 둡니다. 따라서 Brotli Body가 DevTools 표준 content viewer에 표시된다고 보장하지 않습니다.

UTF-8 text/JSON/form request는 postData.text로 내보냅니다. 기타 binary/charset request는 _encoding=base64인 확장 표현입니다. HAR에는 표준 binary request encoding 필드가 없어 표준 HAR import 도구의 request body 표시는 제한됩니다. response가 없으면 HAR convention상 status=0과 _captureStatus를 사용합니다. 미측정 시간은 -1, time은 관측한 nonnegative duration 합이며 전체 경과는 _elapsedMs에 별도로 기록합니다.

HAR schema는 별도 ISC har-schema 프로젝트를 로컬로 vendoring하여 검증했습니다. 공식 HAR 설명을 보완하는 테스트 수단이며 Chrome DevTools 실제 Import는 미완료입니다.

공식 참고:
- https://www.telerik.com/fiddler/fiddler-everywhere/documentation/knowledge-base/fiddler-archives
- https://www.telerik.com/fiddler/fiddlercore/documentation/api/fiddler.sessionflags
- https://www.softwareishard.com/blog/har-12-spec/
- https://docs.mitmproxy.org/stable/api/mitmproxy/http.html
