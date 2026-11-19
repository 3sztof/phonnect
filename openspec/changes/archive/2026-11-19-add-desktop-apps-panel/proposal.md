# Proposal

## Why

Desktop mode shows the phone's desktop, but on current Pixels (Android 16/17) its taskbar and app drawer can't open apps on scrcpy's virtual screen (scrcpy #6699, #7048; fix proposed in #7055, not merged). The simulated-second-screen workaround froze the phone and is opt-in only. Starting an app with `am start --display <id>` does work on the virtual screen (tested on a Pixel 9 Pro, Android 17), and changes nothing on the phone. Tracking issue: [#1](https://github.com/3sztof/phonnect/issues/1).

## What Changes

- **Apps panel** docked to the desktop window (Windows, macOS; floating on Linux), opened once scrcpy reports the new display's id: search the phone's launcher apps, open one on the desktop (full screen by default, or in a window), and list what's open there with Switch to, Close and Desktop (home).
- **A prompt before desktop mode opens**, explaining that it's an experimental workaround: the taskbar can't open apps yet, use the Apps panel, apps have no title bars, nothing on the phone is changed. "Don't show this again" (`desktop_confirmed`). With the opt-in simulated second screen, a stronger warning every time, with how to remove a leftover preview.
- The proper fix stays tracked in `desktop-mode-native-apps` (open).

## Capabilities

### Modified Capabilities
- `desktop-mode`: the Apps panel and the prompt.

## Impact

New `desktop_apps.py` and `_desktop_apps` command; `dialogs.py` (prompt); watcher (prompt hook, display id from scrcpy's output, starting the panel); tray (prompt, setting); docs/usage.md; tests.
