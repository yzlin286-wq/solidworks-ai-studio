param(
  [int]$Port = 8765,
  [string]$Token = "dev-token"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }
$BackendCwd = Join-Path $Root "backend"
$DesktopCwd = Join-Path $Root "apps\desktop"

$env:SWAI_API_HOST = "127.0.0.1"
$env:SWAI_API_PORT = "$Port"
$env:SWAI_API_TOKEN = $Token
$env:SWAI_PROJECT_ROOT = $Root
$env:PYTHONPATH = $BackendCwd

$BackendArgs = @("-m", "uvicorn", "sw_ai_backend.main:app", "--host", "127.0.0.1", "--port", "$Port")
$Backend = Start-Process -FilePath $Python -ArgumentList $BackendArgs -WorkingDirectory $BackendCwd -PassThru -WindowStyle Hidden

try {
  Start-Sleep -Seconds 2
  Push-Location $DesktopCwd
  try {
    $env:SWAI_API_URL = "http://127.0.0.1:$Port"
    $env:VITE_SWAI_API_URL = "http://127.0.0.1:$Port"
    $env:VITE_SWAI_API_TOKEN = $Token
    npm run dev
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
  finally {
    Pop-Location
  }
}
finally {
  if ($Backend -and -not $Backend.HasExited) {
    Stop-Process -Id $Backend.Id
  }
}
