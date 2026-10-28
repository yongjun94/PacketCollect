#!/usr/bin/env bash
set -euo pipefail
python3.12 "$(dirname "$0")/build_desktop.py" macos
