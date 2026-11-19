# Tasks

- [x] `desktop_apps.py`: launcher apps (`cmd package query-activities`), names (`scrcpy --list-apps`), open with `am start --display N --windowingMode 1|5`, open tasks from `dumpsys activity activities`, close with `am stack remove`, home with `input -d N keyevent 3`
- [x] Panel docked like the sidebar; exits with the desktop window; follows light/dark mode
- [x] Watcher reads "New display: ... (id=N)" from scrcpy and starts the panel (virtual screen only)
- [x] Prompt before opening (`_dialog desktop`), "Don't show this again" (`desktop_confirmed`); stronger warning with the simulated second screen
- [x] Live test on Windows with a Pixel 9 Pro (Android 17): prompt, open, switch, close
- [x] docs/usage.md, tests
