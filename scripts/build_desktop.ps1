$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BackendExe = Join-Path $Root "apps\desktop\resources\backend\sw-ai-backend.exe"

if (-not (Test-Path $BackendExe)) {
  & (Join-Path $PSScriptRoot "build_backend.ps1")
}

Push-Location (Join-Path $Root "apps\desktop")
try {
  npm install
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  npm run dist
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Pop-Location
}

Write-Host "Desktop artifacts are emitted under $(Join-Path $Root 'dist')."
