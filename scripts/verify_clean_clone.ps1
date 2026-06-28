param(
  [string]$CloneRoot = "",
  [switch]$SkipBootstrap,
  [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OutputsRoot = Join-Path $Root "outputs"
if (-not $CloneRoot) {
  $CloneRoot = Join-Path $OutputsRoot "clean_clone\latest"
}
$CloneRoot = [System.IO.Path]::GetFullPath($CloneRoot)
$AllowedRoot = [System.IO.Path]::GetFullPath((Join-Path $OutputsRoot "clean_clone"))

if (-not ($CloneRoot -eq $AllowedRoot -or $CloneRoot.StartsWith($AllowedRoot + [System.IO.Path]::DirectorySeparatorChar))) {
  throw "Refusing to manage clone outside outputs/clean_clone: $CloneRoot"
}

New-Item -ItemType Directory -Force -Path $AllowedRoot | Out-Null
if (Test-Path -LiteralPath $CloneRoot) {
  Remove-Item -LiteralPath $CloneRoot -Recurse -Force
}

$Head = (git -C $Root rev-parse HEAD).Trim()
git clone --local --no-hardlinks $Root $CloneRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
git -C $CloneRoot checkout $Head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Report = [ordered]@{
  ok = $false
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  source_root = "<PROJECT_ROOT>"
  clone_root = "outputs/clean_clone/latest"
  commit = $Head
  bootstrap = "not_run"
  backend_pytest = "not_run"
  typecheck = "not_run"
  vitest = "not_run"
  smoke = "not_run"
}

Push-Location $CloneRoot
try {
  if (-not $SkipBootstrap) {
    powershell -ExecutionPolicy Bypass -File (Join-Path $CloneRoot "scripts\bootstrap.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $Report.bootstrap = "passed"
  } else {
    $Report.bootstrap = "skipped"
  }

  $env:PYTHONPATH = Join-Path $CloneRoot "backend"
  python -m pytest backend/tests -q
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  $Report.backend_pytest = "passed"

  npm run typecheck --workspace apps/desktop
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  $Report.typecheck = "passed"

  npm test --workspace apps/desktop
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  $Report.vitest = "passed"

  if (-not $SkipSmoke) {
    npm run smoke --workspace apps/desktop
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $Report.smoke = "passed"
  } else {
    $Report.smoke = "skipped"
  }

  $Report.ok = $true
  Write-Host "Clean clone verification passed at $CloneRoot"
}
finally {
  Pop-Location
  $ReportPath = Join-Path $AllowedRoot "latest_report.json"
  $Report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
}
