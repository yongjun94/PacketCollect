# 검증 보고서 — 2026-10-25 (Asia/Seoul)

현재 결과는 **Windows MVP 소스 구현 및 Linux 자동 검증**입니다. Windows 제품 인수 완료가 아닙니다.

| 항목 | 결과 | 근거/범위 |
|---|---|---|
| Capture Core 정적 분석 | 통과 | Dart analyze, 오류 없음 |
| Capture Export 정적 분석 | 통과 | Dart analyze, 오류 없음 |
| Dart 단위 테스트 | 7/7 통과 | SQLite 재열기/중복 Header/바이너리/쿠키/query/선택·빈 export/실패 정리/복구/입력 거부 |
| Python 테스트 | 12/12 통과 | 실제 HTTP/HTTPS/HTTP2 + addon partial/pause + proxy restore model + JSON Schema |
| Flutter 정적 분석 | 통과 | No issues found |
| Flutter UI/IPC 테스트 | 4/4 통과 | 실제 저장 세션 목록 및 IPC 실패/중지/재시작 검증 |
| Dart native CLI compile + 실행 | 통과 (Linux x64) | 실제 integration store로 9개 세션 SAZ/HAR 생성; native-export-smoke.log |
| HTTP/HTTPS 실제 프록시 수집 | 통과 (Linux) | 사설 origin 서버, upstream CA 검증 유지, proxy CA를 클라이언트에만 trust |
| HTTP/2 | 통과 (Linux) | TLS ALPN h2 양쪽 연결, 중복 Header/Body 바이트 검증 |
| gzip/chunked/binary/redirect | 통과 | 원시 Body 비교, ZIP CRC/XML 및 decoded gzip HAR checksum |
| 연결 실패/일시정지/no-decrypt | 통과 | 8 complete+1 error sample; paused 세션 미저장; no-decrypt TLS 원서버 인증서 확인 |
| CA 생성/독립성 | 통과 (Linux) | 서로 다른 store의 CA 지문이 다름 |
| Windows 빌드 | 불가 | 실제 명령 결과: build windows only supported on Windows hosts |
| Windows HTTPS 실기/CA install·trust·remove | 미검증 | Windows OS 필요 |
| Windows WinINet 실제 적용·복원 | 미검증 | 외부 변경 거부/복원은 fake registry unit test만 검증 |
| Fiddler Classic 실제 Import | 미검증 | 프로그램/실제 Fiddler reference SAZ 없음 |
| Chrome DevTools 실제 HAR Import | 미검증 | 실제 DevTools import 미수행 |
| macOS/mobile/remote capture | 미구현 또는 미검증 | roadmap 참조 |
| 수만 세션/4GiB/장시간 성능 | 미측정 | 성능 수치 주장 없음 |
| Windows 독립 패키지/서명/공증 | 미검증·미구현 | 빌드 스크립트만 제공 |

총 23개 자동 테스트가 통과했습니다. Windows build recipe와 ACL parsing 검증도 포함하지만 mock을 사용한 테스트를 Windows 실기 검증으로 간주하지 않습니다. 테스트 환경은 Python 3.12.14, mitmproxy 12.3.0, Dart 3.9.2, Flutter 3.35.5, Linux x64입니다. Engine runtime dependencies는 universal hash lock으로 고정했고 최신 lock을 설치한 뒤 테스트했습니다.

`artifacts/loopback.saz`와 `.har`는 9개 세션으로, 요청 8개 성공과 연결 실패 1개입니다. 1MiB binary 원본은 integration-summary.json에 SHA-256이 기록되어 있습니다. 시뮬레이션 입력만 포함하며 CA/개인키는 산출물에서 제외했습니다. SAZ의 XML/HTTP 정규화 내용은 docs/saz_format.md에 설명합니다.

## 보안 감사

최초 12.2.1 기반 개발 환경 audit는 9개 패키지에 56개 advisory 항목을 보고했습니다 (중복 ID 포함). mitmproxy 12.3.0과 전이 의존성을 최신 허용 범위로 상향했습니다. runtime hash lock만 설치한 별도 깨끗한 환경에는 **Brotli 1.2.0 한 패키지에 2개 advisory 항목**이 남았습니다. runtime-audit.json에 원본 결과가 있습니다. 이는 서로 다른 ID로 같은 수정 버전 1.2.1을 요구할 수 있으므로 서로 독립된 취약점 2개라고 단정하지 않습니다.

현재 mitmproxy 12.3.0은 Brotli<=1.2.0을 요구합니다. 이 제약을 무시해 미검증 조합을 배포하지 않았습니다. upstream 수정/안전한 dependency 조합을 검증한 후 회사 배포 판단이 필요합니다. msgpack 1.1.2는 이전 개발 환경에만 남아 있었고 최종 runtime lock에는 포함되지 않습니다. python-audit.json은 dev 환경, runtime-audit.json은 최종 runtime inventory 대상입니다. 감사 결과는 exploit 가능성이나 native library CVE 검토 완료를 뜻하지 않습니다.

License text 및 CycloneDX inventory도 깨끗한 runtime과 Flutter package config에서 생성했습니다. Rust/OpenSSL/SQLite/Python/Flutter engine, Windows-only 배포물의 개별 라이선스 검토는 미완료입니다.

## 남은 첫 완료 목표

Windows에서 build → Python/Flutter 없는 clean VM 실행 → 실제 HTTPS 수집 → CA/프록시 인수 테스트 → Fiddler Classic SAZ Import → Chrome HAR Import 결과를 기록해야 합니다. docs/windows_acceptance.md를 기록 양식으로 사용합니다.

## Windows 빌드 준비 추가 결과

PyInstaller로 만든 Linux standalone proxy를 개발용 PYTHONPATH 없이 실행하고 loopback HTTP 및 HTTPS 2개 세션의 바이너리 파일 보존을 검증했습니다. `artifacts/frozen-engine-linux-preflight.json` 참조. Windows 실행 파일은 만들지 않았습니다.

Windows 워크플로와 build manifest/VC++ DLL 수집/패키지 검증/smoke/ZIP 생성을 추가했습니다. 현재 GitHub 연동이나 Windows runner 실행 결과는 없습니다. 실제 .exe 생성에는 Windows 빌드 환경 연결이 필요합니다.
