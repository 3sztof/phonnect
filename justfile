# justfile — scrcpy-autolaunch (legacy Windows-only version)
# Requires: just (https://github.com/casey/just)
#           scrcpy + adb: winget install Genymobile.scrcpy
#
# Run these from a clone of the repo, NOT from %USERPROFILE%\scrcpy-auto.

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

INSTALL_DIR  := join(env_var('USERPROFILE'), 'scrcpy-auto')
STARTUP_DIR  := join(env_var('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
PS_SCRIPT    := join(INSTALL_DIR, 'scrcpy-auto.ps1')
VBS_LAUNCHER := join(INSTALL_DIR, 'scrcpy-auto-launch.vbs')
STARTUP_VBS  := join(STARTUP_DIR, 'scrcpy-auto-launch.vbs')
LOG_FILE     := join(INSTALL_DIR, 'scrcpy-auto.log')
SRC          := justfile_directory()

FIND_WATCHER := "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'powershell.exe' -and $_.CommandLine -like '*scrcpy-auto.ps1*' }"

_default:
    @just --list

# Copy files to %USERPROFILE%\scrcpy-auto and register the Startup entry
install: _guard
    New-Item -ItemType Directory -Force -Path '{{INSTALL_DIR}}' | Out-Null
    Copy-Item -Force '{{SRC}}\scrcpy-auto.ps1' '{{PS_SCRIPT}}'
    Copy-Item -Force '{{SRC}}\scrcpy-auto-launch.vbs' '{{VBS_LAUNCHER}}'
    Copy-Item -Force '{{SRC}}\README.md' '{{INSTALL_DIR}}\README.md'
    Copy-Item -Force '{{VBS_LAUNCHER}}' '{{STARTUP_VBS}}'
    @Write-Host "Installed. Run 'just start' to launch now without logging out."

# Stop the watcher, remove the Startup entry and the install folder
uninstall: _guard stop
    Remove-Item -Force -ErrorAction SilentlyContinue '{{STARTUP_VBS}}'
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue '{{INSTALL_DIR}}'
    @Write-Host 'Uninstalled.'

# Start the watcher now (hidden, via the VBS launcher)
start:
    if ({{FIND_WATCHER}}) { Write-Host 'Watcher already running.' } else { & wscript.exe '{{VBS_LAUNCHER}}'; Write-Host 'Watcher started.' }

# Stop the running watcher (an open scrcpy window stays open)
stop:
    $w = {{FIND_WATCHER}}; if ($w) { $w | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Write-Host 'Watcher stopped.' } else { Write-Host 'No watcher running.' }

# Show whether the watcher is running
status:
    $w = {{FIND_WATCHER}}; if ($w) { Write-Host ('Running, PID ' + ($w.ProcessId -join ', ')) } else { Write-Host 'Not running' }

# Show the last 20 log lines
log:
    if (Test-Path '{{LOG_FILE}}') { Get-Content '{{LOG_FILE}}' -Tail 20 } else { Write-Host 'No log file yet.' }

# Refuse to run install/uninstall from inside the install folder itself
_guard:
    if ((Resolve-Path '{{SRC}}').Path.TrimEnd('\') -ieq '{{INSTALL_DIR}}') { throw 'Run this from a clone of the repo, not from {{INSTALL_DIR}}.' }
