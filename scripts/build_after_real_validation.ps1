$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Report = Join-Path $Root "outputs\validation\latest\REAL_SW2025_VALIDATION_REPORT.json"

if (-not (Test-Path $Report)) {
  Write-Error "Missing real validation report: $Report"
  exit 1
}

$Data = Get-Content -LiteralPath $Report -Encoding UTF8 | ConvertFrom-Json
if (-not $Data.ok) {
  Write-Error "Real SolidWorks 2025 validation did not pass. See $Report"
  exit 1
}

$RequiredCore = @(
  "mcp.solidworks_connect",
  "mcp.solidworks_health_check",
  "mcp.solidworks_new_document",
  "mcp.solidworks_create_basic_part",
  "mcp.solidworks_open_document",
  "mcp.solidworks_save_document",
  "mcp.solidworks_export_active",
  "mcp.solidworks_review_active",
  "mcp.solidworks_add_component",
  "mcp.solidworks_add_coincident_mate",
  "mcp.solidworks_add_distance_mate",
  "mcp.solidworks_add_concentric_mate",
  "mcp.solidworks_set_appearance",
  "mcp.status",
  "mcp.start",
  "mcp.stop",
  "mcp.tool_listing",
  "ai.natural_language_generate_approve_run"
)

$FailedCore = @()
foreach ($CapabilityId in $RequiredCore) {
  $Matches = @($Data.results | Where-Object { $_.capability_id -eq $CapabilityId })
  $Passed = @($Matches | Where-Object { $_.status -eq "passed" })
  $HardFailures = @($Matches | Where-Object { $_.status -in @("failed", "untested") })
  if ($Passed.Count -eq 0 -or $HardFailures.Count -gt 0) {
    $FailedCore += [PSCustomObject]@{
      capability_id = $CapabilityId
      passed = $Passed.Count
      hard_failures = $HardFailures.Count
      statuses = (($Matches | ForEach-Object { $_.status }) -join ",")
      skip_reason = (($Matches | ForEach-Object { $_.skip_reason } | Where-Object { $_ }) -join " | ")
    }
  }
}

if ($FailedCore.Count -gt 0) {
  $FailedCore | Format-Table capability_id,passed,hard_failures,statuses,skip_reason -AutoSize
  Write-Error "Core capability validation failed or was not passed."
  exit 1
}

& (Join-Path $PSScriptRoot "build_backend.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& (Join-Path $PSScriptRoot "build_desktop.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Real validation passed and EXE artifacts were rebuilt."
