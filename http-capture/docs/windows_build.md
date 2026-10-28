# Windows 실행판 빌드 경로 — 2026-10-25

현재 Windows 실행 파일은 아직 생성하지 않았습니다. 이 작업 환경은 Linux이고, 연결된 Windows 빌드 서버가 없습니다. Flutter Windows runner와 PyInstaller Windows 엔진은 Windows에서 빌드해야 합니다. 아래 경로는 실행 준비를 끝낸 빌드 자동화이며 실제 Windows 실행 완료를 의미하지 않습니다.

## GitHub Actions

1. 프로젝트 `http-capture/` 내부 파일을 저장소 루트에 둡니다. `.github/workflows/windows-build.yml`이 저장소 루트의 `.github` 아래에 있어야 합니다.
2. GitHub Actions에서 **Windows development bundle → Run workflow**를 실행합니다.
3. Windows Server 2022 x64 runner가 고정 Flutter/Python을 준비하고 빌드·테스트·패키징합니다.
4. 성공한 run의 **HTTP-Capture-Windows-x64-unsigned** artifact에 `HTTP-Capture-Windows.zip`이 생성됩니다. 압축 전체를 풀고 `HTTP-Capture.exe`를 실행합니다. EXE 하나만 분리해서 복사하면 안 됩니다.

아직 workflow를 원격 저장소에 업로드하거나 실행하지 않았습니다. GitHub 연동도 현재 미연결입니다. workflow는 수동 실행만 허용하고, repository contents 권한은 read이며, 자동 릴리스나 공개 게시를 하지 않습니다. 합성 loopback 테스트만 실행하며 인증서를 OS에 설치하거나 runner의 시스템 프록시를 바꾸지 않습니다. 서드파티 Actions는 조회한 commit SHA로 고정했습니다.

## 로컬 Windows 빌드

Flutter 3.35.5, Python 3.12.x, Visual Studio 2022 Desktop development with C++ 및 Windows SDK를 설치한 개발 환경에서:

```powershell
.\scripts\build_windows.ps1
```

빌드 스크립트는 Python 엔진/runtime inventory용 가상환경을 각각 새로 생성합니다. Flutter release build 후 SQLite DLL 경로를 추가해서 테스트를 실행합니다. Flutter/Dart 테스트와 패키지 파일 검증에 실패하면 ZIP을 생성하지 않습니다.

## 이번 수정

- Windows `.bat` 호출의 공백 경로 인용, 한국어 계정에서도 SID를 얻는 바이트 처리.
- SQLite DLL이 준비된 후 Flutter/Dart 테스트 수행.
- Visual Studio redistributable 디렉터리에서 app-local VC++ x64 DLL 수집. 누락 시 실패. 재배포 라이선스 승인은 별도 검토.
- Windows CA/private key가 번들에 포함되면 실패.
- standalone Python 엔진을 frozen 상태로 실행하여 HTTP/HTTPS 바이너리 2개 세션의 Body 파일을 검증.
- Python이 별도 설치되지 않은 사용자에게 배포할 수 있도록 proxy 폴더 포함. 실제 clean Windows 검증은 아직 필요.
- SHA-256 build manifest 및 서명되지 않은 개발용 ZIP 생성.
- 앱 중복 실행에 대한 OS 파일 잠금, startup 오류 화면.
- 프로세스 exit보다 마지막 stdout 이벤트가 늦게 도착하는 경우를 처리. 중지 후 최종 이벤트가 유실된 것으로 오인하지 않도록 drain 후 상태 변경.

## 실제 실행 검증이 남은 항목

- Actions workflow 실제 실행과 Windows EXE/패키지 실행.
- Windows CurrentUser CA 설치·신뢰·삭제 및 WinINet 적용·종료·강제 종료 복구.
- Fiddler Classic SAZ Import / Chrome DevTools HAR Import.
- Python/Flutter/VC++ 개발 도구 없는 clean Windows PC.
- 코드 서명, 라이선스 검토, Brotli dependency advisory 해결/평가.

Linux에서 PyInstaller standalone proxy 빌드와 두 세션 HTTP/HTTPS smoke test가 통과했습니다. 이 결과는 Windows 바이너리 빌드나 실행 검증을 대신하지 않습니다.
