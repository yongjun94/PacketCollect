# 라이선스 검토 자료

프로젝트 자체 배포 라이선스는 소유자가 아직 지정하지 않았습니다. 독립 구현 소스이며 Fiddler 코드/브랜드 자산을 포함하지 않습니다.

mitmproxy 자체는 MIT이며 실제 설치 distribution에서 고지 전문을 수집합니다. 의존성은 별개입니다. THIRD_PARTY_NOTICES.json과 texts/는 현재 Linux 개발 환경의 설치 패키지 evidence입니다. dev/build 도구도 보수적으로 포함됩니다. Python/Flutter 엔진과 Rust/OpenSSL/SQLite native 전이 의존성 및 Windows-only pydivert 등 최종 포함물은 별도로 확인해야 합니다. 회사 상업 배포 적합성에 대한 법률 승인 자료는 아닙니다.

빌드 스크립트는 대상 OS에서 notice와 CycloneDX package inventory를 다시 생성합니다. SBOM에 모든 native 정적 링크 구성요소까지 들어간다고 주장하지 않습니다. Flutter 내장 라이선스 UI는 Dart/plugin 고지를 제공하고 Python 고지는 배포 폴더에 포함합니다.
