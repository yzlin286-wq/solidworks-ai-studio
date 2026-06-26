$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

Set-Location $Root

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw "Node.js 20+ is required."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm is required."
}

if (-not (Test-Path $Python)) {
  python -m venv $Venv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "backend\requirements.txt")

Push-Location (Join-Path $Root "apps\desktop")
try {
  npm install
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Pop-Location
}

& (Join-Path $PSScriptRoot "sync_solidworks_skill.ps1")
& (Join-Path $PSScriptRoot "sync_taste_skill.ps1")

Write-Host "Bootstrap complete. Run scripts/dev.ps1 to start the app."
