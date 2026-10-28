# License review status / 라이선스 검토 현황

Status: **INCOMPLETE — technical preview, not a compliance approval.**

This record distinguishes verified evidence from unresolved distribution work. It does not select a license for the project's own code or conclude that a distribution is unlawful. Assessment must follow the actual recipient, package, component version and applicable terms.

## Evidence checked

The Windows preview from CI run 40652755920 (source `ff41434306fb65004d379ace2fcb614b1890a4e3`, artifact 12799813358) was inspected. Its ZIP includes WinDivert DLL/driver files, windows-redirector.exe, PyDivert and THIRD_PARTY_NOTICES/REVIEW_REQUIRED files. This is actual package evidence, not just a dependency declaration.

| Component | Observed evidence | Open work |
|---|---|---|
| mitmproxy 12.3.0 | MIT text included | Retain version-specific copyright/license evidence. |
| mitmproxy-windows 0.12.15 / WinDivert | LGPL metadata and native binaries present | Verify selected terms, exact native source/build inputs and applicable source/recombination obligations. |
| PyDivert 3.1.3 | LGPL-3.0-or-later OR GPL-2.0-or-later declared | Record the applicable license choice and comply with its conditions. |
| ldap3 2.9.1 / urwid 4.0.13 | LGPL notices included | Review source delivery and the frozen Python packaging/replacement mechanism. |
| certifi 2026.10.23 | MPL-2.0 notice included | Provide appropriate covered-source availability notice. |
| mitmproxy_rs 0.12.15 | Windows generated notices report UNRESOLVED and no notice files | Resolve version-specific license/native dependencies and add evidence. |
| Native/runtime components | Current collection script explicitly excludes full native/runtime approval | Review Rust crates, OpenSSL, Python, Flutter engine, SQLite and platform binaries separately. |
| Android | Separate Dart/Kotlin engine, without the desktop Python bundle | Review the actual APK, Flutter/native libraries and BouncyCastle notices separately. |
| Project-owned code | No top-level project license was identified during review | Rights holder must choose publication/distribution terms. Third-party licenses remain separate. |

The source-tree SBOM can differ from a platform build's generated inventory. Neither automatically proves that a package contains only permitted components or that all obligations have been fulfilled. Private repository access does not itself resolve external distribution obligations.

## Next steps before broad redistribution

1. Inventory the exact Windows ZIP, Mac ZIP and Android APK, including native files and transitive dependencies.
2. Resolve UNKNOWN/UNRESOLVED entries against the exact upstream versions and original notices.
3. Decide whether unused components can be excluded; test the resulting packages rather than deleting imports or notices blindly.
4. Provide the applicable licenses, source availability, corresponding source/build/recombination materials and notices for the chosen distribution method.
5. Review the project's own code ownership, license and any workplace publication approvals.
6. Have the organization’s OSS/legal reviewer assess the finished distribution set. Keep evidence and approval scope with the release.

LGPL does not automatically require the entire independent application to be published under LGPL. Its source, notice and recombination/replacement conditions still require version- and packaging-specific evaluation. A separate process or PyInstaller's exception does not eliminate the obligations of the dependencies being conveyed.

## Primary references

- [mitmproxy MIT license](https://github.com/mitmproxy/mitmproxy/blob/main/LICENSE)
- [mitmproxy-windows 0.12.15 metadata](https://pypi.org/project/mitmproxy-windows/0.12.15/)
- [PyDivert license choices](https://github.com/ffalcinelli/pydivert/blob/main/LICENSE)
- [LGPL v3](https://www.gnu.org/licenses/lgpl-3.0.html)
- [Mozilla MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
- [PyInstaller license exception](https://pyinstaller.org/en/stable/license.html)

한국어 요약: mitmproxy 자체의 MIT 허용 범위와 실제 배포물에 포함된 LGPL/MPL 등의 의무를 구분합니다. 고지·SBOM 수집은 이루어졌지만 소스 제공·재결합·네이티브 구성 요소와 자체 코드의 라이선스 선택은 미완료입니다. 실행 파일은 기술 검증용이며 외부 배포 검토 완료로 표시하지 않습니다.
