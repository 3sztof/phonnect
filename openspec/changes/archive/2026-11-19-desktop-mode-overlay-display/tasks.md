# Tasks

- [x] Research: scrcpy #6699, #6936, #7048, #7125, PR #7055 (unmerged; still broken in 5.0.1)
- [x] Live test on a Pixel 9 Pro, Android 17: simulated second screen + `--display-id`; apps open; normal mouse works
- [x] `OverlayDisplayKeeper` (save, set, restore `overlay_display_devices`) and adb global-setting helpers
- [x] `open_desktop`: find the new display id with `scrcpy --list-displays`; fallback to `--new-display`; `desktop_method` setting
- [x] Restore on desktop close, on quit (desktop windows close too) and on reconnect; not when only the mirror closes
- [x] Sidebar and tray don't wait; failures become notifications; notification about the phone preview
- [x] docs/usage.md, tests
