#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
project_root="$PWD"
(cd packages/capture_core && dart pub get --enforce-lockfile && dart analyze)
(cd packages/capture_export && dart pub get --enforce-lockfile && dart analyze && dart test)
CAPTURE_ARTIFACTS="$project_root/artifacts" python -m pytest tests/unit tests/integration -q
python -m pytest tests/har_compatibility -q
(cd apps/capture_app && flutter pub get --enforce-lockfile && flutter analyze && flutter test)
