# Proposal

## Why

Tracking issue: [#6](https://github.com/3sztof/scrcpy-autolaunch/issues/6).

Every time the mirror opens, it appears in scrcpy's default position and size, so the user drags it back to their preferred spot each time.

## What Changes

- Remember each phone's mirror window position and size when it closes, and reopen it there next time.
- If the saved position is no longer visible (monitor disconnected, resolution changed), fall back to the default position.
- Windows first (the sidebar already tracks the window's bounds); on macOS/Linux use what scrcpy and the window system allow.

Out of scope: remembering the desktop-mode window (could follow later), multi-window layouts.

## Capabilities

### New Capabilities
- `mirror-window`: options for how the mirror window behaves, including its remembered position and size.

### Modified Capabilities
<!-- none -->

## Impact

Watcher (scrcpy window position/size arguments), sidebar or watcher tracking the window bounds, remembered-phones storage, docs/usage.md, tests.
