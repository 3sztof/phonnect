#Requires -Version 5.1
# Installs scrcpy-autolaunch with uv (installing uv first if needed, after asking).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install.ps1 [-Source <path or git URL>]
param([string]$Source = "")

$ErrorActionPreference = "Stop"

if (-not $Source) {
    $repo = Split-Path -Parent $PSScriptRoot
    if (Test-Path (Join-Path $repo "pyproject.toml")) { $Source = $repo }
    else { $Source = "git+https://github.com/3sztof/scrcpy-autolaunch" }
}

function Assert-Success([string]$what) {
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)." }
}

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) {
    Write-Host "uv (https://docs.astral.sh/uv/) is required but not installed."
    Write-Host "It would be installed with the official installer:"
    Write-Host "  powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
    Write-Host "(installs to $env:USERPROFILE\.local\bin and adds that folder to your user PATH)"
    if ((Read-Host "Install uv now? [y/N]") -notmatch '^[yY]') { throw "Aborted: uv is required." }
    powershell -NoProfile -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (-not (Test-Path $uv)) { throw "uv was installed, but not found at $uv. Open a new terminal and run this again." }
}

$bin = (& $uv tool dir --bin).Trim()
$app = Join-Path $bin "scrcpy-autolaunch.exe"

# A running instance locks its files on Windows; stop it before reinstalling.
if (Test-Path $app) { & $app stop | Out-Host }

Write-Host "Installing scrcpy-autolaunch from $Source ..."
& $uv tool install --force --reinstall --python ">=3.11" $Source
Assert-Success "uv tool install"

Write-Host ""
& $app doctor | Out-Host
Write-Host ""
& $app install
Assert-Success "scrcpy-autolaunch install"

if (-not (($env:Path -split ';') -contains $bin)) {
    Write-Host ""
    Write-Host "Note: $bin is not on your PATH. Run 'uv tool update-shell' to use 'scrcpy-autolaunch' directly."
}
