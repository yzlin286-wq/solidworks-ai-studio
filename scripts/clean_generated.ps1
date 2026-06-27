param(
  [switch]$DryRun,
  [switch]$ConfirmDestructive
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Removed = @()

function Assert-InWorkspace {
  param([Parameter(Mandatory = $true)][string]$Path)
  $resolved = (Resolve-Path -LiteralPath $Path).Path
  if (-not ($resolved -eq $Root -or $resolved.StartsWith($Root + [System.IO.Path]::DirectorySeparatorChar))) {
    throw "Refusing to remove path outside workspace: $resolved"
  }
  return $resolved
}

function Remove-WithRetry {
  param([Parameter(Mandatory = $true)][string]$LiteralPath)
  if ($DryRun) {
    return
  }
  for ($attempt = 1; $attempt -le 5; $attempt++) {
    try {
      if (Test-Path -LiteralPath $LiteralPath) {
        Remove-Item -LiteralPath $LiteralPath -Recurse -Force -ErrorAction Stop
      }
      return
    } catch {
      if ($attempt -eq 5) { throw }
      Start-Sleep -Milliseconds (250 * $attempt)
    }
  }
}

function Remove-WorkspacePath {
  param([Parameter(Mandatory = $true)][string]$RelativePath)
  $target = Join-Path $Root $RelativePath
  if (-not (Test-Path -LiteralPath $target)) { return }
  $resolved = Assert-InWorkspace $target
  Remove-WithRetry -LiteralPath $resolved
  $script:Removed += $resolved
}

$paths = @(
  ".venv",
  "node_modules",
  "apps\desktop\node_modules",
  "apps\desktop\dist",
  "apps\desktop\out",
  "apps\desktop\test-results",
  "apps\desktop\playwright-report",
  "apps\desktop\.vite",
  "backend\build",
  "backend\dist",
  "backend\generated",
  "dist",
  "outputs",
  ".pytest_cache",
  "test-results",
  "playwright-report",
  "coverage",
  "logs",
  "tmp",
  "temp"
)

if (-not $DryRun -and -not $ConfirmDestructive) {
  throw "Refusing destructive cleanup without -ConfirmDestructive. Run with -DryRun first, then rerun with -ConfirmDestructive only when the target list is correct."
}

foreach ($path in $paths) {
  Remove-WorkspacePath $path
}

Get-ChildItem -LiteralPath $Root -Recurse -Force -Directory -Filter "__pycache__" |
  Where-Object { $_.FullName.StartsWith($Root + [System.IO.Path]::DirectorySeparatorChar) } |
  ForEach-Object {
    Remove-WithRetry -LiteralPath $_.FullName
    $Removed += $_.FullName
  }

Get-ChildItem -LiteralPath $Root -Recurse -Force -File |
  Where-Object {
    $_.FullName.StartsWith($Root + [System.IO.Path]::DirectorySeparatorChar) -and
    @(".pyc", ".pyo", ".tsbuildinfo") -contains $_.Extension.ToLowerInvariant()
  } |
  ForEach-Object {
    Remove-WithRetry -LiteralPath $_.FullName
    $Removed += $_.FullName
  }

[pscustomobject]@{
  root = $Root
  dry_run = [bool]$DryRun
  removed_count = $Removed.Count
  removed = $Removed
} | ConvertTo-Json -Depth 4
