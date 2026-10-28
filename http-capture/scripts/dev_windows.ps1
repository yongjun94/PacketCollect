$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.build\dev'
py -3.12 -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'venv failed' }
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install --require-hashes -r (Join-Path $root 'engines\desktop_proxy\requirements.lock')
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed' }
$env:HTTP_CAPTURE_PYTHON = $python
$env:PYTHONPATH = Join-Path $root 'engines\desktop_proxy\src'
Push-Location (Join-Path $root 'apps\capture_app')
try {
    flutter pub get --enforce-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Flutter dependencies failed' }
    flutter run -d windows
    if ($LASTEXITCODE -ne 0) { throw 'Flutter run failed' }
} finally { Pop-Location }
