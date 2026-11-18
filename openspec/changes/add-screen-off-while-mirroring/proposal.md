# Proposal

## Why

Tracking issue: [#2](https://github.com/3sztof/phonnect/issues/2).

When the phone is mirrored on the computer, its own screen is usually not needed: it drains the battery and lights up on the desk. Keeping it dark while mirroring is a common feature of other scrcpy front ends.

## What Changes

- New setting **Turn the phone screen off while mirroring**, off by default, in the tray's Settings submenu.
- When on, the phone's screen turns off as soon as the mirror window opens. The mirror keeps working, and the phone's screen comes back on when the window closes, the app quits, or the setting is switched off.
- Optional: a sidebar toggle for the current window (scrcpy's own Alt+O / Alt+Shift+O keep working).

Out of scope: locking the phone, changing the phone's screen timeout or brightness settings.

Open question: check whether scrcpy reliably turns the screen back on when it exits (and over Wi-Fi drops); if not, the app has to do it, following the phone-settings restore guarantee.

## Capabilities

### New Capabilities
- `mirror-window`: options for how the mirror window and the phone behave while mirroring (screen off, always on top, window position).

### Modified Capabilities
- `phone-settings`: the phone's screen state joins the settings that are changed temporarily and always restored.

## Impact

Watcher (scrcpy arguments, live toggle), tray Settings submenu, sidebar, config (`screen_off`), docs/usage.md, tests.
