#Requires -Version 5.1
# Phonnect uninstaller for Windows.
#
#   irm https://github.com/3sztof/phonnect/releases/latest/download/uninstall.ps1 | iex
#
# Options, as environment variables or as parameters with -File:
#   PHONNECT_PURGE=1 / -Purge   also delete settings, logs and remembered phones (otherwise it asks)
#   PHONNECT_PURGE=0 / -Keep    keep them (otherwise it asks)
#   PHONNECT_YES=1   / -Yes     answer yes to every question
#
# Removes only what the installer added. uv, scrcpy and adb stay; the end of the output says how to remove them.
param([switch]$Purge, [switch]$Keep, [switch]$Yes)

function Uninstall-Phonnect {
    param([string]$PurgeChoice, [bool]$Yes)

    $ErrorActionPreference = "Stop"
    function Step([string]$t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor White }
    function Ok([string]$t) { Write-Host "  + " -ForegroundColor Green -NoNewline; Write-Host $t }
    function Row([string]$k, [string]$v) { Write-Host ("  {0,-16} {1}" -f $k, $v) }
    function Short([string]$p) { if ($p.StartsWith($env:USERPROFILE)) { "~" + $p.Substring($env:USERPROFILE.Length) } else { $p } }
    function Ask([string]$q, [bool]$default) {
        if ($Yes) { return $default }
        $hint = if ($default) { "[Y/n]" } else { "[y/N]" }
        $a = Read-Host "$q $hint"
        if (-not $a) { return $default }
        return $a -match '^[yY]'
    }

    if (-not $PurgeChoice) { $PurgeChoice = $env:PHONNECT_PURGE }
    if ($env:PHONNECT_YES -eq "1") { $Yes = $true }

    $uv = (Get-Command uv -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if (-not $uv) { $p = Join-Path $env:USERPROFILE ".local\bin\uv.exe"; if (Test-Path $p) { $uv = $p } }
    $bin = Join-Path $env:USERPROFILE ".local\bin"
    $toolsDir = Join-Path $env:APPDATA "uv\tools"
    if ($uv) { $bin = (& $uv tool dir --bin).Trim(); $toolsDir = (& $uv tool dir).Trim() }
    $app = Join-Path $bin "phonnect.exe"
    $settings = Join-Path $env:LOCALAPPDATA "phonnect"
    $programs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $entries = @((Join-Path $programs "Startup\Phonnect.lnk"), (Join-Path $programs "Phonnect.lnk")) | Where-Object { Test-Path $_ }

    Write-Host ""
    Write-Host "Phonnect uninstaller" -ForegroundColor White
    Step "This will remove"
    $hasApp = Test-Path $app
    $hasData = Test-Path $settings
    if ($hasApp) {
        Row "App" "$(Short $toolsDir)\phonnect  (stopped first; phone settings it changed are put back)"
        Row "Commands" "$(Short $bin)\phonnect.exe, phonnect-tray.exe"
    }
    foreach ($e in $entries) { Row "Entry" (Short $e) }
    if ($hasData) { Row "Settings, log" "$(Short $settings)  (only if you choose to below)" }
    if (-not $hasApp -and -not $entries -and -not $hasData) {
        Write-Host "  Phonnect isn't installed for this user. Nothing to do."
        return
    }
    Write-Host ""
    Write-Host "  Not touched: uv, scrcpy, adb, and anything on your phone."
    Write-Host ""
    if (-not (Ask "Uninstall Phonnect?" $true)) { Write-Host "Nothing changed."; return }
    $doPurge = $false
    if ($hasData) {
        if ($PurgeChoice -eq "1") { $doPurge = $true }
        elseif ($PurgeChoice -ne "0") { $doPurge = Ask "Also delete settings, logs and remembered Wi-Fi phones? (keep them to reinstall later)" $false }
    }

    Step "Removing"
    if ($hasApp) {
        if ($doPurge) { & $app uninstall --purge | Out-Host } else { & $app uninstall | Out-Host }
        & $uv tool uninstall phonnect
        if ($LASTEXITCODE -ne 0) { throw "uv could not remove the app (see above)." }
        Ok "Removed the app"
    } else {
        foreach ($e in $entries) { Remove-Item -LiteralPath $e; Ok "Removed $(Short $e)" }
        if ($doPurge) { Remove-Item -LiteralPath $settings -Recurse -Force; Ok "Deleted $(Short $settings)" }
    }
    if ($hasData -and -not $doPurge) { Ok "Kept your settings in $(Short $settings)" }

    Step "Done"
    Write-Host "  Phonnect is removed. If you don't need these anymore, remove them too:"
    Row "uv" "https://docs.astral.sh/uv/getting-started/installation/#uninstallation"
    Row "scrcpy, adb" "winget uninstall Genymobile.scrcpy   (if you installed it with winget)"
}

$choice = if ($Purge) { "1" } elseif ($Keep) { "0" } else { "" }
try {
    Uninstall-Phonnect -PurgeChoice $choice -Yes:$Yes.IsPresent
} catch {
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($PSCommandPath) { exit 1 }
}
