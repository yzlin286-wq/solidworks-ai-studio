$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
  powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "clean_generated.ps1") -DryRun
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "bootstrap.ps1")
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  $env:PYTHONPATH = Join-Path $Root "backend"
  python -m pytest backend/tests -q
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  npm run typecheck --workspace apps/desktop
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  npm test --workspace apps/desktop
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  npm run smoke --workspace apps/desktop
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  Write-Host "Clean clone verification passed."
}
finally {
  Pop-Location
}
