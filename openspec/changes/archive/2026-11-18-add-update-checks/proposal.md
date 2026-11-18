# Proposal

## Why

Tracking issue: [#5](https://github.com/3sztof/phonnect/issues/5).

scrcpy updates often and newer features (desktop mode, audio duplication) need recent versions. Neither scrcpy nor Phonnect told the user when an update was available, and updating Phonnect meant finding the release page and typing a uv command.

## What Changes

- At most once a day, ask GitHub's API for the latest release of Phonnect and of scrcpy (cached in the state folder). Nothing else is sent.
- If Phonnect has a newer release, the tray menu shows **Update Phonnect to X.Y.Z…**. Clicking it opens a terminal window that runs that release's installer in update mode: it asks, stops the app (phone settings are put back), replaces it and starts it again.
- If scrcpy has a newer release, the menu shows **scrcpy X.Y is available…**, which explains how to update it for the way it was installed (winget, scoop, Homebrew, …). scrcpy is not updated automatically: it belongs to the OS package manager.
- `phonnect update [--check]` does the same from a terminal.
- Settings: **Check for updates (once a day)** (on by default), **Check for updates now**, and the installed version at the end of the Settings menu.

## Capabilities

### New Capabilities
- `update-checks`: telling the user when Phonnect or scrcpy can be updated, and updating Phonnect.

### Modified Capabilities
- `tray-menu`: shows the update entries.

## Impact

New `updates.py`, tray menu and tooltip, `check_updates` setting, `phonnect update`, docs (usage, installation), tests with the network faked.
