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
  & $Python -m sw_ai_backend.skills.capabilities
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  @'
from pathlib import Path
from sw_ai_backend.skills.capabilities import CapabilityRegistry
from sw_ai_backend.core.paths import validation_latest_dir

registry = CapabilityRegistry()
response = registry.write()
target = validation_latest_dir() / "capability_matrix.csv"
registry.write_csv(target, response.capabilities)
print(target)
'@ | & $Python -
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Pop-Location
}
