$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

$env:PYTHONPATH = $Backend
$env:SWAI_PROJECT_ROOT = $Root
$env:SWAI_OUTPUT_DIR = Join-Path $Root "outputs"

Push-Location $Root
try {
  & $Python -m sw_ai_backend.validation.visual_validation
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Pop-Location
}
