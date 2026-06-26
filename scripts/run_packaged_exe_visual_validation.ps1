$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

$env:PYTHONPATH = $Backend
$env:SWAI_PROJECT_ROOT = $Root
$env:SWAI_OUTPUT_DIR = Join-Path $Root "outputs"
$env:SWAI_VISUAL_MAX_VISION_IMAGES = "12"

Push-Location $Root
try {
  node (Join-Path $PSScriptRoot "packaged_exe_visual_validation.mjs")
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $Python -m sw_ai_backend.validation.visual_validation
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Remove-Item Env:\SWAI_VISUAL_MAX_VISION_IMAGES -ErrorAction SilentlyContinue
  Pop-Location
}
