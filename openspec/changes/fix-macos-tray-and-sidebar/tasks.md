# Tasks

- [x] Tray: hand menu/icon/tooltip/notification/quit updates to the main thread on macOS (`PyObjCTools.AppHelper.callAfter`)
- [x] Watcher: `phones()` no longer reaps (no adb calls while building the menu)
- [x] Sidebar: `MacDock` with Quartz window bounds, topmost only while the mirror or the bar is in front, no Dock icon
- [x] Icons: white / black outline matching the menu bar; refresh on light/dark changes
- [x] pyobjc Cocoa + Quartz as explicit macOS dependencies
- [ ] Try on a Mac: close a mirror window, move it, minimize it, switch apps
