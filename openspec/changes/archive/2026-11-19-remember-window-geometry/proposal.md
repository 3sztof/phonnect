# Proposal

## Why

Tracking issue: [#6](https://github.com/3sztof/phonnect/issues/6).

Every time the mirror opens, it appears in scrcpy's default position and size. On wide screens (for example 3440x1440), scrcpy's first window is also too wide for a phone, so it opens with black bars at the sides, and the user shrinks it by hand every time.

## What Changes

- Windows: remember each phone's window position and height, separately for portrait and landscape and for the desktop-mode window, and reopen it there.
- Only the height and position go to scrcpy (`--window-height`, `--window-x`, `--window-y`). scrcpy then works out the width from the phone's picture, so a reopened window has no black bars.
- When a window opens with black bars anyway (first time, or after rotating), trim them once scrcpy reports the picture size ("Texture: WxH"), keeping the height.
- If the saved position is on a monitor that's gone, keep the size and let scrcpy choose the position.
- Setting **Reopen windows where they were** (on by default, Windows only). Window places set in the user's own `scrcpy_args` win.

Out of scope: macOS and Linux (scrcpy picks the size and position there), multi-window layouts.

## Capabilities

### New Capabilities
- `mirror-window`: where the mirror window opens and how big it is.

## Impact

New `window_memory.py`; `osutil.py` (window rectangle in the window's own DPI mode, resize by content size, monitor check); watcher (launch arguments, following windows once a second, reading the picture size from scrcpy's output); tray setting; `remember_window` config; docs/usage.md; tests.
