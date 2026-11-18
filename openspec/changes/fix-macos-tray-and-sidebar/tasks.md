# Tasks

- [x] Tray: hand menu/icon/tooltip/notification/quit updates to the main thread on macOS (`PyObjCTools.AppHelper.callAfter`)
- [x] Watcher: `phones()` no longer reaps (no adb calls while building the menu)
- [x] Sidebar: `MacDock` with Quartz window bounds, topmost only while the mirror or the bar is in front, no Dock icon
- [x] Sidebar width in points on macOS (was scaled as if 96 dpi, so the buttons didn't fit), and never narrower than its buttons need
- [x] Icons: white / black outline matching the menu bar; refresh on light/dark changes
- [x] pyobjc Cocoa + Quartz as explicit macOS dependencies
- [x] The app bundle starts the tray in the background (`phonnect start`) and exits. It used to become the tray, and macOS ended that process seconds after opening (no icon, nothing in the log)
- [x] Opening Phonnect while it runs opens its menu (macOS) or says where the icon is
- [ ] Try on a Mac: close a mirror window, move it, minimize it, switch apps
