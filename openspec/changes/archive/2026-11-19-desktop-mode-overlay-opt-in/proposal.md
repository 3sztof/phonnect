# Proposal

## Why

The simulated-second-screen workaround (v0.4.4) made apps open on a Pixel 9 Pro, but in real use it froze after about 20 seconds: the phone stopped accepting clicks, the preview stayed on its screen after the desktop window closed, desktop mode couldn't be opened again, and Android restarted itself. On a Mac, apps launched but didn't show in the desktop window. Changing a phone setting that can crash Android breaks the promise that Phonnect leaves the phone as it found it.

## What Changes

- Desktop mode goes back to scrcpy's virtual screen by default (`desktop_method: "virtual"`). On current Pixels its taskbar shows but can't open apps, until scrcpy's fix ([#7055](https://github.com/Genymobile/scrcpy/pull/7055)) is released.
- The simulated second screen stays available as an explicit, documented, experimental opt-in (`desktop_method: "overlay"`), with the freeze and the recovery steps described.
- Issue #1 is reopened.

## Capabilities

### Modified Capabilities
- `desktop-mode`: the virtual screen is the default; the simulated second screen is opt-in.

## Impact

`config.py` default, watcher check, docs/usage.md, tests.
