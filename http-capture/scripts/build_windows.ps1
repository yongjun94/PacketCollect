$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
py -3.12 (Join-Path $PSScriptRoot 'build_desktop.py') windows
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed' }
