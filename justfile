# phonnect: run `just` to list the recipes.

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
    uv tool uninstall phonnect

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

# Lint and format check (same as CI), plus the pre-commit hooks if installed
lint:
    uv run ruff check
    uv run ruff format --check

# Fix what ruff can fix and format the code
fmt:
    uv run ruff check --fix
    uv run ruff format

# Type check with ty (experimental, not enforced yet)
typecheck:
    uvx ty check src

# Bump the version, tag vX.Y.Z and push; CI then publishes the GitHub Release
release version:
    uv run python scripts/release.py {{version}}

# Run the tray from this checkout (foreground)
dev-tray:
    uv run phonnect tray

# Run the console watcher from this checkout (foreground, Ctrl+C to stop)
dev-run:
    uv run phonnect run

[windows]
_app *args:
    @& (Join-Path (uv tool dir --bin).Trim() 'phonnect.exe') {{args}}

[unix]
_app *args:
    @"$(uv tool dir --bin)/phonnect" {{args}}
