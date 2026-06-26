$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
  python -m venv $Venv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "backend\requirements.txt")

Push-Location (Join-Path $Root "backend")
try {
  & $Python -m PyInstaller --clean --noconfirm pyinstaller.spec
}
finally {
  Pop-Location
}

$Source = Join-Path $Root "backend\dist\sw-ai-backend.exe"
$DestinationDir = Join-Path $Root "apps\desktop\resources\backend"
$Destination = Join-Path $DestinationDir "sw-ai-backend.exe"
New-Item -ItemType Directory -Force -Path $DestinationDir | Out-Null
Copy-Item -Force $Source $Destination

Write-Host "Backend EXE ready: $Destination"
