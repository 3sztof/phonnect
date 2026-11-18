#Requires -Version 5.1
# Phonnect installer for Windows.
#
#   irm https://github.com/3sztof/phonnect/releases/latest/download/install.ps1 | iex
#
# Options, as environment variables (irm | iex can't pass arguments) or as parameters with -File:
#   PHONNECT_VERSION=X.Y.Z   / -Version X.Y.Z   install that release instead of the latest
#   PHONNECT_SOURCE=path|url / -Source ...      install from a local checkout, wheel or git URL (developers)
#   PHONNECT_UPDATE=1        / -Update          only replace the app; keep start-at-login and settings
#   PHONNECT_NO_DEPS=1       / -NoDeps          don't offer to install scrcpy / adb
#   PHONNECT_YES=1           / -Yes             answer yes to every question
#
# Everything goes into your user account; no admin rights needed.
# Remove it again with:
#   irm https://github.com/3sztof/phonnect/releases/latest/download/uninstall.ps1 | iex
param([string]$Version = "", [string]$Source = "", [switch]$Update, [switch]$NoDeps, [switch]$Yes)

function Install-Phonnect {
    param([string]$Version, [string]$Source, [bool]$Update, [bool]$NoDeps, [bool]$Yes)

    $ErrorActionPreference = "Stop"
    $Repo = "3sztof/phonnect"
    $DefaultVersion = ""  # set by the release workflow, so each release's script installs that release
    $Releases = "https://github.com/$Repo/releases"
    $UninstallCmd = "irm $Releases/latest/download/uninstall.ps1 | iex"

    function Step([string]$t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor White }
    function Ok([string]$t) { Write-Host "  + " -ForegroundColor Green -NoNewline; Write-Host $t }
    function Warn([string]$t) { Write-Host "  ! " -ForegroundColor Yellow -NoNewline; Write-Host $t }
    function Row([string]$k, [string]$v) { Write-Host ("  {0,-16} {1}" -f $k, $v) }
    function Short([string]$p) { if ($p.StartsWith($env:USERPROFILE)) { "~" + $p.Substring($env:USERPROFILE.Length) } else { $p } }
    function Ask([string]$q, [bool]$default) {
        if ($Yes) { return $true }
        $hint = if ($default) { "[Y/n]" } else { "[y/N]" }
        $a = Read-Host "$q $hint"
        if (-not $a) { return $default }
        return $a -match '^[yY]'
    }
    function Find-Cmd([string]$name, [string[]]$dirs) {
        $c = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($c) { return $c.Source }
        foreach ($d in $dirs) { $p = Join-Path $d "$name.exe"; if (Test-Path $p) { return $p } }
        return $null
    }

    if (-not $Version) { $Version = $env:PHONNECT_VERSION }
    if (-not $Version) { $Version = $DefaultVersion }
    if (-not $Source) { $Source = $env:PHONNECT_SOURCE }
    if ($env:PHONNECT_UPDATE -eq "1") { $Update = $true }
    if ($env:PHONNECT_NO_DEPS -eq "1") { $NoDeps = $true }
    if ($env:PHONNECT_YES -eq "1") { $Yes = $true }
    $Version = $Version -replace '^v', ''

    # -- what's here already --------------------------------------------------
    $local = $env:LOCALAPPDATA
    $userBin = Join-Path $env:USERPROFILE ".local\bin"
    $wingetDirs = @(Get-ChildItem (Join-Path $local "Microsoft\WinGet\Packages") -Directory -Filter "Genymobile.scrcpy_*" -ErrorAction SilentlyContinue |
        ForEach-Object { Get-ChildItem $_.FullName -Directory -Filter "scrcpy-win64-*" } | Sort-Object LastWriteTime -Descending | ForEach-Object FullName)
    $toolDirs = $wingetDirs + @((Join-Path $env:USERPROFILE "scoop\shims"), (Join-Path $local "Android\Sdk\platform-tools"))

    $uv = Find-Cmd "uv" @($userBin, (Join-Path $env:USERPROFILE ".cargo\bin"))
    $scrcpy = Find-Cmd "scrcpy" $toolDirs
    $adb = Find-Cmd "adb" $toolDirs
    $winget = Find-Cmd "winget" @()

    $toolsDir = Join-Path $env:APPDATA "uv\tools"
    $bin = $userBin
    if ($uv) {
        $toolsDir = (& $uv tool dir).Trim()
        $bin = (& $uv tool dir --bin).Trim()
    }
    $app = Join-Path $bin "phonnect.exe"
    $settings = Join-Path $local "phonnect"
    $programs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $loginEntry = Join-Path $programs "Startup\Phonnect.lnk"
    $menuEntry = Join-Path $programs "Phonnect.lnk"

    if (-not $Source) {
        if (-not $Version) {
            try { $Version = ((Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest").tag_name) -replace '^v', '' }
            catch { throw "Could not reach GitHub to find the latest release: $($_.Exception.Message)" }
        }
        if ($Version -notmatch '^\d{1,4}(\.\d{1,4}){1,3}$') { throw "Not a release version: '$Version'" }
        $Source = "$Releases/download/v$Version/phonnect-$Version-py3-none-any.whl"
        $what = "Phonnect $Version"
    } else {
        $what = "Phonnect from $Source"
    }
    $installed = ""
    if (Test-Path $app) { $installed = ((& $app --version) -split ' ')[-1] }

    # -- the plan -------------------------------------------------------------
    Write-Host ""
    Write-Host "Phonnect installer" -ForegroundColor White -NoNewline
    Write-Host "  your Android phone on your desktop, via scrcpy + adb" -ForegroundColor DarkGray

    if ($Update) {
        Step "Update"
        Row "Installed" $(if ($installed) { $installed } else { "not found" })
        Row "New" $what
        Row "Steps" "stop the app (phone settings it changed are put back), replace it, start it again"
        Row "Kept" "settings, remembered phones, start at login"
        if (-not $uv) { throw "uv was not found. Run the full installer instead (without PHONNECT_UPDATE)." }
        Write-Host ""
        if (-not (Ask "Update now?" $true)) { Write-Host "Nothing changed."; return }
    } else {
        Step "This will install"
        Row "Phonnect" ($what + $(if ($installed) { " (replacing $installed)" } else { "" }))
        Row "App files" "$(Short $toolsDir)\phonnect  (its own Python environment, managed by uv)"
        Row "Commands" "$(Short $bin)\phonnect.exe, phonnect-tray.exe"
        Row "Settings, log" (Short $settings)
        Row "Start at login" (Short $loginEntry)
        Row "Start menu" (Short $menuEntry)
        Write-Host ""
        Write-Host "  It needs:"
        Row "uv" $(if ($uv) { "found: $(Short $uv)" } else { "missing: installs Python apps; you'll be asked before it's installed to ~\.local\bin" })
        Row "scrcpy" $(if ($scrcpy) { "found: $(Short $scrcpy)" } else { "missing: mirrors the phone's screen" })
        Row "adb" $(if ($adb) { "found: $(Short $adb)" } else { "missing: talks to the phone (comes with scrcpy)" })
        Write-Host ""
        Write-Host "  Nothing is changed on your phone, and no admin rights are needed."
        Write-Host "  Not listed under Windows 'Installed apps': uv manages it. To remove it later:"
        Write-Host "    $UninstallCmd"
        Write-Host ""
        if (-not (Ask "Continue?" $true)) { Write-Host "Nothing changed."; return }
    }

    # -- uv -------------------------------------------------------------------
    if (-not $uv) {
        Step "Installing uv"
        Write-Host "  uv (https://docs.astral.sh/uv/) installs Phonnect and the Python it needs, separate from"
        Write-Host "  any other Python. The official installer would run:"
        Write-Host "    powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
        Write-Host "  It puts uv in ~\.local\bin and adds that folder to your user PATH."
        Write-Host "  Remove it later: https://docs.astral.sh/uv/getting-started/installation/#uninstallation"
        if (-not (Ask "Install uv?" $true)) { throw "uv is required. Install it yourself, then run this again." }
        powershell -NoProfile -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        $uv = Find-Cmd "uv" @($userBin)
        if (-not $uv) { throw "uv was installed, but it can't be found. Open a new terminal and run this again." }
        $bin = (& $uv tool dir --bin).Trim()
        $app = Join-Path $bin "phonnect.exe"
        Ok "uv installed: $(Short $uv)"
    }

    # -- scrcpy and adb -------------------------------------------------------
    if (-not $Update -and -not $NoDeps -and (-not $scrcpy -or -not $adb)) {
        Step "scrcpy and adb"
        if ($winget) {
            $cmd = "winget install --id Genymobile.scrcpy --exact --source winget"
            Write-Host "  scrcpy comes with adb. winget installs it for your user only and keeps it up to date"
            Write-Host "  (winget upgrade Genymobile.scrcpy). This would run:"
            Write-Host "    $cmd"
            if (Ask "Install them now?" $true) {
                winget install --id Genymobile.scrcpy --exact --source winget --accept-package-agreements --accept-source-agreements
                if ($LASTEXITCODE -ne 0) { Warn "That didn't work. Install scrcpy yourself; Phonnect waits for it (red icon)." }
            } else {
                Warn "Skipped. Phonnect shows a red icon until scrcpy and adb are installed."
            }
        } else {
            Warn "winget isn't available. Get scrcpy (includes adb) from https://github.com/Genymobile/scrcpy/releases"
            Warn "or with Scoop: scoop install scrcpy"
        }
    }

    # -- Phonnect -------------------------------------------------------------
    Step "Installing $what"
    # A running copy locks its files; stopping it also puts back what it changed on the phones.
    if (Test-Path $app) { & $app stop | Out-Host }
    $old = Join-Path $bin "scrcpy-autolaunch.exe"
    if (Test-Path $old) {
        Write-Host "  Replacing the old scrcpy-autolaunch ..."
        & $old stop | Out-Host
        & $uv tool uninstall scrcpy-autolaunch
    }
    & $uv tool install --force --reinstall --python ">=3.11" $Source
    if ($LASTEXITCODE -ne 0) { throw "uv could not install $Source (see above). A previous version, if any, is still there: phonnect start" }
    Ok "Installed $(& $app --version)"

    if ($Update) {
        & $app start | Out-Host
    } else {
        Step "Checking scrcpy, adb and your phone"
        & $app doctor | Out-Host
        Step "Start at login, Start menu entry, starting the app"
        & $app install | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "phonnect install failed (see above)." }
    }

    # -- done -----------------------------------------------------------------
    Step "Done"
    Write-Host "  Look for the phone icon in the tray, near the clock. Plug in your phone with USB debugging on,"
    Write-Host "  and its screen opens on your desktop. Phone setup: https://github.com/$Repo/blob/main/docs/phone-setup.md"
    Write-Host ""
    Row "Commands" "phonnect status | doctor | start | stop | update"
    Row "Uninstall" $UninstallCmd
    if (-not (($env:Path -split ';') -contains $bin)) {
        Write-Host ""
        Warn "$(Short $bin) is not on your PATH yet, so 'phonnect' isn't found in this window. Open a new terminal, or run: uv tool update-shell"
    }
    $env:PHONNECT_RESULT = "ok"  # read by the update window started from the tray
}

try {
    Install-Phonnect -Version $Version -Source $Source -Update:$Update.IsPresent -NoDeps:$NoDeps.IsPresent -Yes:$Yes.IsPresent
} catch {
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    # Run as a file (just install): fail the command. Run through irm | iex: don't close the user's window.
    if ($PSCommandPath) { exit 1 }
}
