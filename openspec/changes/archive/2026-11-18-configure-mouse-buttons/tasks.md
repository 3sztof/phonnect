# Tasks

## 1. Behavior

- [x] 1.1 Add `mouse_buttons` to the config with the new defaults (right: app, middle: home, back: back, forward: recents)
- [x] 1.2 Translate it to `--mouse-bind=<primary>:bhsn` for mirror and desktop-mode windows; skip for scrcpy older than 2.5 or when the user set `--mouse-bind` in `scrcpy_args`
- [x] 1.3 Tray: Settings → Mouse buttons submenu with a radio group per button; changing reopens open windows

## 2. Tests and docs

- [x] 2.1 Unit tests: default argument, custom bindings, version gate, user override, invalid config values fall back to defaults
- [x] 2.2 Live check on the phone: default right click no longer goes back
- [x] 2.3 docs/usage.md: mouse buttons section and config key; README if needed
