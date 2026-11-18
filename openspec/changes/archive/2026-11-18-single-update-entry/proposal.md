# Proposal

## Why

After 0.4.0, the tray showed a separate "scrcpy X.Y is available…" entry, which drew attention to something Phonnect can't update, while updating Phonnect itself (the part users care about) took a click plus a confirmation in a terminal.

## What Changes

- One updates entry in the tray menu: **Check for updates** (checks now and reports Phonnect's and scrcpy's state in one notification), which becomes **Update Phonnect to X.Y.Z** when a new release exists.
- Clicking Update is the confirmation: the update runs without asking again in a small terminal window, which closes by itself when it worked and stays open when it didn't.
- No separate scrcpy entry: a newer scrcpy, and the command that updates it, is mentioned in the Check for updates result.
- The setting is renamed **Check for updates automatically**.

## Capabilities

### Modified Capabilities
- `update-checks`: one-click update; scrcpy news only in the check result.
- `tray-menu`: a single updates entry.

## Impact

`tray.py`, `updates.py` (`confirm`), `install.ps1` (reports success to the update window), docs.
