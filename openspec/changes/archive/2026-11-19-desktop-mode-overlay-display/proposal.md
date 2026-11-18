# Proposal

## Why

Closes the problem behind issue [#1](https://github.com/3sztof/phonnect/issues/1): desktop mode showed the Pixel desktop and taskbar, but clicking an app did nothing, on two different phones. It's a known Android 16/17 + scrcpy problem ([scrcpy #6699](https://github.com/Genymobile/scrcpy/issues/6699), [#6936](https://github.com/Genymobile/scrcpy/issues/6936), [#7048](https://github.com/Genymobile/scrcpy/issues/7048)): the launcher only opens apps on displays it treats as desktop-capable, and scrcpy's virtual displays (with system decorations) aren't. A fix for scrcpy is proposed ([#7055](https://github.com/Genymobile/scrcpy/pull/7055)) but not merged, and still broken in scrcpy 5.0.1. Android's own simulated second screen works: tested live on a Pixel 9 Pro (Android 17), apps open as windows.

## What Changes

- Desktop mode turns on Android's simulated second screen (global setting `overlay_display_devices`, *Developer options → Simulate secondary displays*) with the configured size and density, finds its display id, and opens scrcpy on it (`--display-id`). The normal mouse works (no captured pointer needed).
- The setting is saved first and removed when the desktop window closes, on quit, or when the phone reconnects if it was gone. This is an exception to "nothing on the phone changes": it's restored like rotation and content size.
- The phone shows a semi-transparent preview of the simulated screen while it's on (Android's design, can't be hidden). A notification and the docs say so.
- If the simulated screen doesn't appear within a few seconds, fall back to scrcpy's virtual display (the old behaviour). `desktop_method: "virtual"` always uses that.
- Opening takes a few seconds now, so the sidebar and tray don't wait for it; problems become a notification.

## Capabilities

### Modified Capabilities
- `desktop-mode`: works on current Pixels; temporary, restored phone setting.

## Impact

`phone_state.py` (`OverlayDisplayKeeper`), `adb.py` (global settings), watcher (`open_desktop`, display list, restore on close and quit), tray and control (non-blocking), `desktop_method` config, docs/usage.md, tests.
