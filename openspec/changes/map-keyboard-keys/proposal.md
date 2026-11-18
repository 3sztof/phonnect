# Proposal

## Why

Tracking issue: [#12](https://github.com/3sztof/scrcpy-autolaunch/issues/12).

Using the phone from the keyboard should feel natural: Escape for Back, a key for Home, one for the app switcher, configurable to taste.

## What Changes

Findings so far (Pixel 9 Pro, Android 17):
- **Escape already acts as Back.** Android treats an unhandled Escape key as Back (tested: Escape left the Wi-Fi settings screen). No work needed beyond documenting it.
- **The Windows key is taken by Windows**: pressing it alone opens the Start menu, and Win+letter combinations are system shortcuts that win over any app. scrcpy also uses left Win (and left Alt) as its shortcut modifier: Alt+B Back, Alt+H Home, Alt+S Recent apps, Alt+N notifications.

Proposed:
- A **Keyboard shortcuts** settings window listing actions (Back, Home, Recent apps, Notifications, Quick settings, Power, Volume) with a key for each, defaults: Escape → Back (Android's own), F1 → Home, F2 → Recent apps, F3 → Notifications.
- Keys are only taken over while the mirror (or desktop-mode) window is in front; everywhere else they behave normally.
- Using the Windows key itself (e.g. Win alone → Home) needs a Windows-only low-level keyboard hook that suppresses the Start menu while the mirror is focused. Offer it as an opt-in, Windows-only option, after a prototype shows it's reliable.

Out of scope: game-style key-to-touch mapping (QtScrcpy's niche), macOS/Linux global key capture (Wayland doesn't allow it; macOS needs accessibility permission).

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `audio-and-input`: keyboard keys can trigger phone actions while the mirror is focused.

## Impact

A key-capture mechanism while the mirror is focused (Windows: keyboard hook in the sidebar process, which already has a message loop; elsewhere: scrcpy's own shortcuts only), a settings window, config (`key_bindings`), docs/usage.md, tests. Needs a prototype before committing to the Windows-key option.
