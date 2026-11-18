# Proposal

## Why

Tracking issue: [#5](https://github.com/3sztof/scrcpy-autolaunch/issues/5).

scrcpy updates often and newer features (desktop mode, audio duplication) need recent versions. Neither scrcpy nor this app currently tells the user when an update is available.

## What Changes

- At most once a day, check GitHub for the latest release of scrcpy and of scrcpy-autolaunch.
- If one is newer than what's installed, show a quiet entry in the tray menu (no popups), e.g. "scrcpy 3.4 is available", which shows how to update: the OS-specific command for scrcpy (`winget upgrade Genymobile.scrcpy`, `brew upgrade scrcpy`, ...) and the `uv tool install --force …` command for the app.
- A setting to turn update checks off. No data is sent other than the request to GitHub.

Out of scope: installing updates automatically.

## Capabilities

### New Capabilities
- `update-checks`: telling the user when scrcpy or the app can be updated.

### Modified Capabilities
- `tray-menu`: shows the update entry.

## Impact

New update-check module (network access, caching of the last check), tray menu, config (`check_updates`), docs/usage.md, tests (with network mocked).
