$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Installer = Join-Path $Root "dist\SolidWorks AI Studio Setup.exe"

if (-not (Test-Path $Installer)) {
  throw "Installer not found: $Installer"
}

Push-Location $Root
try {
  Write-Host "Installing SolidWorks AI Studio from $Installer"
  $process = Start-Process -FilePath $Installer -ArgumentList "/S", "/currentuser" -PassThru -Wait
  Write-Host "Installer exit code: $($process.ExitCode)"
  Start-Sleep -Seconds 5

  $shortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\SolidWorks AI Studio.lnk"
  $exe = $null
  if (Test-Path $shortcut) {
    $shell = New-Object -ComObject WScript.Shell
    $exe = $shell.CreateShortcut($shortcut).TargetPath
  }
  if (-not $exe -or -not (Test-Path $exe)) {
    $candidates = Get-ChildItem -Path "$env:LOCALAPPDATA\Programs", "$env:ProgramFiles" -Recurse -Filter "SolidWorks AI Studio.exe" -ErrorAction SilentlyContinue
    $exe = ($candidates | Select-Object -First 1 -ExpandProperty FullName)
  }
  if (-not $exe -or -not (Test-Path $exe)) {
    throw "Installed EXE was not found after installation."
  }

  $env:SWAI_INSTALLED_EXE = $exe
  $env:SWAI_OUTPUT_DIR = Join-Path $Root "outputs"
  node (Join-Path $PSScriptRoot "installed_exe_full_validation.mjs")
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Remove-Item Env:\SWAI_INSTALLED_EXE -ErrorAction SilentlyContinue
  Remove-Item Env:\SWAI_OUTPUT_DIR -ErrorAction SilentlyContinue
  Pop-Location
}
