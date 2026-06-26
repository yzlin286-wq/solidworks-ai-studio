param(
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Target = Join-Path $Root "vendor\skills\taste-skill"
$Repo = "https://github.com/Leonxlnx/taste-skill"

if (-not (Test-Path $Target)) {
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
  git clone $Repo $Target
  exit 0
}

if (-not (Test-Path (Join-Path $Target ".git"))) {
  Write-Host "Existing directory is not a git checkout; leaving it unchanged: $Target"
  exit 0
}

$Dirty = git -C $Target status --porcelain
if ($Dirty -and -not $Force) {
  Write-Host "Local changes detected in $Target. Re-run with -Force only after reviewing those changes."
  exit 0
}

git -C $Target pull --ff-only
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Could not update $Target from the network. Keeping the existing local checkout."
  exit 0
}
