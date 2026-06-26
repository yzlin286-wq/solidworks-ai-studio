$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Latest = Join-Path $Root "outputs\validation\latest"
$RealReport = Join-Path $Latest "REAL_SW2025_VALIDATION_REPORT.json"
$StrictReport = Join-Path $Latest "STRICT_TRUTH_REPORT.json"
$VisualReport = Join-Path $Root "outputs\visual_validation\latest\VISUAL_VALIDATION_REPORT.json"
$RuntimeReport = Join-Path $Latest "PACKAGED_EXE_RUNTIME_REPORT.json"
$SecretScan = Join-Path $Latest "security_secret_scan.json"
$ReopenManifest = Join-Path $Latest "solidworks_reopen_manifest.json"
$LlmValidation = Join-Path $Latest "llm_api_validation.json"
$BackendExe = Join-Path $Root "apps\desktop\resources\backend\sw-ai-backend.exe"
$Installer = Join-Path $Root "dist\SolidWorks AI Studio Setup.exe"
$Portable = Join-Path $Root "dist\SolidWorks AI Studio Portable.exe"
$CannotClaim = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("5b2T5YmN5LiN6IO95a6j56ew5omA5pyJ5Yqf6IO955yf5a6e5Y+v55So44CC"))

foreach ($Path in @($RealReport, $StrictReport, $VisualReport, $RuntimeReport, $SecretScan, $ReopenManifest, $LlmValidation, $BackendExe, $Installer, $Portable)) {
  if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error "Missing required strict validation artifact: $Path"
    exit 1
  }
}

$Real = Get-Content -LiteralPath $RealReport -Encoding UTF8 | ConvertFrom-Json
if (-not $Real.ok) {
  Write-Error "REAL_SW2025_VALIDATION_REPORT.json is not ok=true."
  exit 1
}

$Strict = Get-Content -LiteralPath $StrictReport -Encoding UTF8 | ConvertFrom-Json
if (-not $Strict.strict_ok) {
  Write-Host $CannotClaim
  $Strict.summary | Format-List
  if ($Strict.skipped.Count -gt 0) { $Strict.skipped | Format-Table id,reason -AutoSize }
  if ($Strict.untested.Count -gt 0) { $Strict.untested | Select-Object -First 80 | ForEach-Object { Write-Host "untested: $_" } }
  Write-Error "STRICT_TRUTH_REPORT.json is not strict_ok=true."
  exit 1
}

$Visual = Get-Content -LiteralPath $VisualReport -Encoding UTF8 | ConvertFrom-Json
if (-not $Visual.visual_ok) {
  Write-Error "VISUAL_VALIDATION_REPORT.json is not visual_ok=true."
  exit 1
}

$Runtime = Get-Content -LiteralPath $RuntimeReport -Encoding UTF8 | ConvertFrom-Json
if (-not $Runtime.packaged_exe_ok) {
  Write-Error "PACKAGED_EXE_RUNTIME_REPORT.json is not packaged_exe_ok=true."
  exit 1
}
if (-not $Runtime.natural_language_ui_run_attempted -or -not $Runtime.natural_language_ui_run_completed) {
  Write-Error "Packaged EXE did not complete the natural-language UI SolidWorks run."
  exit 1
}

$Reopen = Get-Content -LiteralPath $ReopenManifest -Encoding UTF8 | ConvertFrom-Json
if (-not $Reopen.ok) {
  $Reopen.entries | Where-Object { $_.reopen_attempted -and -not $_.reopen_passed } | Select-Object -First 20 kind,file_path,reason | Format-Table -AutoSize
  Write-Error "solidworks_reopen_manifest.json is not ok=true."
  exit 1
}

$Llm = Get-Content -LiteralPath $LlmValidation -Encoding UTF8 | ConvertFrom-Json
if (-not $Llm.ok) {
  Write-Error "llm_api_validation.json is not ok=true."
  exit 1
}

$Secret = Get-Content -LiteralPath $SecretScan -Encoding UTF8 | ConvertFrom-Json
if (-not $Secret.ok) {
  $Secret.findings | Format-Table path,match_count -AutoSize
  Write-Error "security_secret_scan.json found potential API key leakage."
  exit 1
}

& (Join-Path $PSScriptRoot "build_backend.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& (Join-Path $PSScriptRoot "build_desktop.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Strict truth validation passed and EXE artifacts were rebuilt."
