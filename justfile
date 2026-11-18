# justfile — scrcpy-autolaunch
# Requires: just (https://github.com/casey/just)
#            scrcpy + adb via winget install Genymobile.scrcpy
#
# Usage:
#   just install      — copy files and register startup entry
#   just uninstall    — remove startup entry and all files
#   just start        — start the watcher right now (without logging out)
#   just stop         — kill any running watcher instance
#   just log          — tail the last 20 lines of the event log
#   just status       — show whether the watcher is currently running

INSTALL_DIR  := join(env_var('USERPROFILE'), 'scrcpy-auto')
STARTUP_DIR  := join(env_var('APPDATA'), 'Microsoft\Windows\Start Menu\Programs\Startup')
PS_SCRIPT    := join(INSTALL_DIR, 'scrcpy-auto.ps1')
VBS_LAUNCHER := join(INSTALL_DIR, 'scrcpy-auto-launch.vbs')
STARTUP_VBS  := join(STARTUP_DIR, 'scrcpy-auto-launch.vbs')
LOG_FILE     := join(INSTALL_DIR, 'scrcpy-auto.log')

# Install: copy files to %USERPROFILE%\scrcpy-auto and register startup entry
install:
    @echo Installing scrcpy-autolaunch to {{INSTALL_DIR}} ...
    powershell -Command "New-Item -ItemType Directory -Force -Path '{{INSTALL_DIR}}' | Out-Null"
    powershell -Command "Copy-Item -Force '{{justfile_directory()}}\scrcpy-auto.ps1'          '{{PS_SCRIPT}}'"
    powershell -Command "Copy-Item -Force '{{justfile_directory()}}\scrcpy-auto-launch.vbs'   '{{VBS_LAUNCHER}}'"
    powershell -Command "Copy-Item -Force '{{justfile_directory()}}\README.md'                '{{join(INSTALL_DIR, 'README.md')}}'"
    powershell -Command "Copy-Item -Force '{{VBS_LAUNCHER}}' '{{STARTUP_VBS}}'"
    @echo Done. Startup entry registered. Run 'just start' to launch now without logging out.

# Uninstall: stop watcher, remove startup entry and install folder
uninstall:
    @echo Stopping watcher (if running) ...
    -just stop
    @echo Removing startup entry ...
    powershell -Command "Remove-Item -Force -ErrorAction SilentlyContinue '{{STARTUP_VBS}}'"
    @echo Removing install folder ...
    powershell -Command "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue '{{INSTALL_DIR}}'"
    @echo Uninstall complete.

# Start the watcher now (uses the VBS launcher so there is no console window)
start:
    powershell -Command " \
        $w = Get-Process powershell -ErrorAction SilentlyContinue | \
             Where-Object { $_.CommandLine -like '*scrcpy-auto.ps1*' }; \
        if ($w) { Write-Host 'Watcher is already running (PID ' + $w.Id + ')' } \
        else    { Start-Process wscript.exe -ArgumentList '\"{{VBS_LAUNCHER}}\"'; \
                  Write-Host 'Watcher started.' }"

# Stop the running watcher
stop:
    powershell -Command " \
        $w = Get-Process powershell -ErrorAction SilentlyContinue | \
             Where-Object { $_.CommandLine -like '*scrcpy-auto.ps1*' }; \
        if ($w) { $w | Stop-Process -Force; Write-Host 'Watcher stopped.' } \
        else    { Write-Host 'No watcher running.' }"

# Show the last 20 log lines
log:
    powershell -Command "if (Test-Path '{{LOG_FILE}}') { Get-Content '{{LOG_FILE}}' -Tail 20 } else { Write-Host 'No log file yet.' }"

# Show whether the watcher process is running
status:
    powershell -Command " \
        $w = Get-Process powershell -ErrorAction SilentlyContinue | \
             Where-Object { $_.CommandLine -like '*scrcpy-auto.ps1*' }; \
        if ($w) { Write-Host ('Running  PID ' + ($w.Id -join ', ')) } \
        else    { Write-Host 'Not running' }"
