# scrcpy-autolaunch: run `just` to list the recipes.

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

_default:
    @just --list

# Install uv if needed (asks first), the app and its dependencies; enable start at login; start the tray
[windows]
install:
    powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "{{justfile_directory()}}\scripts\install.ps1" -Source "{{justfile_directory()}}"

# Install uv if needed (asks first), the app and its dependencies; enable start at login; start the tray
[unix]
install:
    sh "{{justfile_directory()}}/scripts/install.sh" "{{justfile_directory()}}"

# Stop the app, remove start at login, settings, logs and the uv tool
uninstall:
    -just _app uninstall --purge
    uv tool uninstall scrcpy-autolaunch

# Start the tray app in the background
start:
    @just _app start

# Stop the tray app (open scrcpy windows stay open)
stop:
    @just _app stop

# Show whether it's running, start-at-login state and file locations
status:
    @just _app status

# Check scrcpy, adb, tray support and connected devices
doctor:
    @just _app doctor

# Show the end of the log
log lines="30":
    @just _app log -n {{lines}}

# Run the unit tests
test:
    uv run pytest -q

# Run the tray from this checkout (foreground)
dev-tray:
    uv run scrcpy-autolaunch tray

# Run the console watcher from this checkout (foreground, Ctrl+C to stop)
dev-run:
    uv run scrcpy-autolaunch run

[windows]
_app *args:
    @& (Join-Path (uv tool dir --bin).Trim() 'scrcpy-autolaunch.exe') {{args}}

[unix]
_app *args:
    @"$(uv tool dir --bin)/scrcpy-autolaunch" {{args}}
