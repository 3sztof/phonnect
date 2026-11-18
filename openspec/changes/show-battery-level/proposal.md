# Proposal

## Why

Tracking issue: [#8](https://github.com/3sztof/phonnect/issues/8).

While mirroring over Wi-Fi the phone isn't charging, and the user usually isn't looking at it, so a dying battery comes as a surprise.

## What Changes

- Show each connected phone's battery level and charging state in its tray entry and in the tray icon's tooltip.
- Notify once when a mirrored phone that isn't charging drops below 15%.
- Refresh at a low rate (about once a minute) to avoid extra load on the phone.

Out of scope: battery history, charging control.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `tray-menu`: phone entries and the tooltip show battery level; low-battery notification.

## Impact

Watcher (periodic battery reading over adb), tray menu and tooltip, docs/usage.md, tests.
