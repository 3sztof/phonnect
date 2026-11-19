# Proposal

## Why

Tracking issue: [#1](https://github.com/3sztof/phonnect/issues/1).

Desktop mode should work like plugging the phone into a monitor: open apps from the desktop's own taskbar and app drawer, in windows with title bars that can be moved, resized and closed. On current Pixels (Android 16/17) that doesn't work on scrcpy's virtual screen: the launcher only opens apps on displays it treats as desktop-capable, and scrcpy's virtual displays (with system decorations) aren't. Today Phonnect works around it with the Apps panel (archived change `add-desktop-apps-panel`), and offers the simulated second screen only as a risky opt-in (it froze a Pixel 9 Pro).

Upstream status (2026-11-19):
- scrcpy issues [#6699](https://github.com/Genymobile/scrcpy/issues/6699), [#6936](https://github.com/Genymobile/scrcpy/issues/6936), [#7048](https://github.com/Genymobile/scrcpy/issues/7048), [#7125](https://github.com/Genymobile/scrcpy/issues/7125): open.
- Fix proposed in [PR #7055](https://github.com/Genymobile/scrcpy/pull/7055): on Android 17, create the virtual display with `VIRTUAL_DISPLAY_FLAG_ALLOWS_CONTENT_MODE_SWITCH` instead of `SHOULD_SHOW_SYSTEM_DECORATIONS`, and without `OWN_CONTENT_ONLY`. Not merged; scrcpy 5.0.1 still has the problem.

## What Changes (once scrcpy ships the fix)

- Check desktop mode with the first scrcpy release that includes it, on a Pixel with Android 16 and 17: apps open from the taskbar, in windows with title bars.
- From that scrcpy version on: no Apps panel by default (keep it as an option, or remove it), a shorter prompt or none, and drop the simulated-second-screen opt-in if it's no longer needed.
- Older scrcpy versions keep today's workaround, and the prompt suggests updating scrcpy.
- Close issue #1.

Not planned: bundling or patching scrcpy (Phonnect uses the scrcpy from the user's package manager).

## Capabilities

### Modified Capabilities
- `desktop-mode`: the desktop's own taskbar works; the workaround is only used with older scrcpy.

## Impact

Watcher (scrcpy version check for the panel and prompt), dialogs, docs/usage.md, issue #1.
