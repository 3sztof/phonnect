# Proposal

## Why

Tracking issue: [#11](https://github.com/3sztof/scrcpy-autolaunch/issues/11).

scrcpy turns a right click into the phone's Back button and a middle click into Home. Users expect a right click to act like a right click, and an unexpected Back throws them out of the screen they were on.

## What Changes

- New defaults for mouse buttons in the mirror window:
  - right click: sent to the app (like a right click on a PC; most apps ignore it, some show a menu)
  - middle click: Home (unchanged)
  - side "back" button (mouse button 4): Back, matching what it does in a browser
  - side "forward" button (mouse button 5): Recent apps
- Holding Shift while clicking keeps scrcpy's original shortcuts (Back, Home, Recent apps, Notifications), so nothing is lost.
- A tray submenu **Settings → Mouse buttons** to choose, per button, between sending the click to the app, a phone action (Back, Home, Recent apps, Notifications) and nothing.
- Changing a binding reopens an open mirror window to apply it.

Out of scope: keyboard key mappings (tracked separately in #12), touchpad gestures, scroll behavior.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `audio-and-input`: mouse buttons in the mirror window become configurable, with new defaults.

## Impact

Config (`mouse_buttons`), watcher (scrcpy's mouse-binding option, needs scrcpy 2.5+), tray Settings submenu, docs/usage.md, tests.
