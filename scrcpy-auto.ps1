# scrcpy-auto.ps1
# Watches for a USB-connected Android device and launches scrcpy automatically.
# Logs events to scrcpy-auto.log in the same folder.
# --no-audio keeps phone audio on the phone (scrcpy 2.0+ forwards it by default).

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
$LOG        = Join-Path $SCRIPT_DIR "scrcpy-auto.log"

# ── Resolve scrcpy and adb ───────────────────────────────────────────────────
# Prefer whatever is on PATH; fall back to the default winget install location.
function Resolve-Exe {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    # winget default for Genymobile.scrcpy
    $wingetBase = Join-Path $env:LOCALAPPDATA `
        "Microsoft\WinGet\Packages"
    $found = Get-ChildItem -Path $wingetBase -Filter "$Name.exe" -Recurse `
             -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { return $found.FullName }

    throw "Cannot find $Name. Install scrcpy via: winget install Genymobile.scrcpy"
}

$ADB    = Resolve-Exe "adb"
$SCRCPY = Resolve-Exe "scrcpy"

# ── Named mutex: allow only one watcher instance ────────────────────────────
$mutexName = "Global\ScrcpyAutoWatcher"
$mutex     = New-Object System.Threading.Mutex($false, $mutexName)
$acquired  = $false
try {
    $acquired = $mutex.WaitOne(0)
} catch [System.Threading.AbandonedMutexException] {
    $acquired = $true
}

if (-not $acquired) {
    exit 0  # another instance is already running
}

# ── Logging helper ───────────────────────────────────────────────────────────
function Write-Log {
    param([string]$Message)
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LOG -Value $line -Encoding UTF8

    # Trim log to last ~800 KB when it exceeds 1 MB
    try {
        $file = Get-Item -LiteralPath $LOG -ErrorAction Stop
        if ($file.Length -gt 1MB) {
            $content = Get-Content -LiteralPath $LOG -Encoding UTF8
            $keep    = [Math]::Floor($content.Count * 0.8)
            Set-Content -LiteralPath $LOG -Value ($content | Select-Object -Last $keep) -Encoding UTF8
            Add-Content -LiteralPath $LOG -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  [log trimmed to stay under 1 MB]" -Encoding UTF8
        }
    } catch {}
}

# ── Helper: is a USB device currently attached? ──────────────────────────────
function Test-DeviceAttached {
    try {
        # Parse `adb devices`; look for at least one non-offline entry.
        # Robust against offline emulators appearing alongside real devices.
        $lines = & $ADB devices 2>$null | Select-Object -Skip 1
        foreach ($line in $lines) {
            if ($line -match '\S') {
                $parts = $line -split '\s+'
                if ($parts.Count -ge 2 -and $parts[1] -eq 'device') {
                    return $true
                }
            }
        }
        return $false
    } catch {
        return $false
    }
}

# ── Main loop ────────────────────────────────────────────────────────────────
Write-Log "Watcher started (PID $PID)"

try {
    while ($true) {

        # Block until a device appears
        & $ADB wait-for-device 2>$null
        Write-Log "Device connected"

        # Launch scrcpy with no console window; the mirror window still appears.
        # --select-usb pins to the physical USB device, ignoring offline
        # emulators or tcpip devices that may also appear in `adb devices`.
        # --no-audio stops scrcpy from capturing (and muting) device audio.
        Write-Log "Starting scrcpy"
        $psi                  = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName         = $SCRCPY
        $psi.Arguments        = "--no-audio --stay-awake --select-usb"
        $psi.UseShellExecute  = $false
        $psi.CreateNoWindow   = $true
        $proc = [System.Diagnostics.Process]::Start($psi)
        $proc.WaitForExit()
        Write-Log "scrcpy exited (code $($proc.ExitCode))"

        # Wait until the device is physically unplugged before looping.
        # This prevents closing the window from instantly relaunching scrcpy.
        Write-Log "Waiting for device to be removed..."
        while (Test-DeviceAttached) {
            Start-Sleep -Seconds 2
        }
        Write-Log "Device removed"
    }
}
finally {
    Write-Log "Watcher stopping (PID $PID)"
    if ($acquired) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
