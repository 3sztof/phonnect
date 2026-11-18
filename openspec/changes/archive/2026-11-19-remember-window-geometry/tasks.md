# Tasks

- [x] `window_memory.py`: per phone and orientation (and desktop mode), saved in `windows.json`; launch arguments with height and position only; drop positions that are off screen
- [x] `osutil.py`: content rectangle in the window's own DPI mode, resize to a content size, monitor check
- [x] Watcher: launch arguments for the mirror and desktop windows; follow windows once a second; read "Texture: WxH" from scrcpy's output; trim black bars once per picture shape
- [x] `remember_window` setting and tray toggle (Windows only); user's own window arguments win
- [x] Tested live on Windows (3440x1440): a 1145x1360 first window trimmed to 612x1360, reopened at the same place and size
- [x] docs/usage.md, tests
