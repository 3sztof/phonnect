# Proposal

## Why

Reports from a Mac: closing the scrcpy window froze the whole app (the terminal it ran in stopped responding and the menu bar icon could no longer be clicked); the sidebar floated at the screen edge instead of sitting next to the mirror window; and the grey menu bar icon didn't match the other, white icons.

Cause of the freeze: AppKit may only be used from the main thread, but the tray updated its menu and icon from the watcher's thread. The menu, being built on the main thread, also waited for the watcher's lock while the watcher, holding it, was updating the menu.

## What Changes

- Tray updates (menu, icon, tooltip, notifications, quit) are handed to the main thread on macOS. Building the menu no longer does the clean-up after a closed window (which talks to the phone over adb); the watcher loop does that within a second.
- macOS sidebar docking: follows the scrcpy window using Quartz's window list (no Screen Recording permission needed), stays above the mirror only while it or the bar is in front, hides when the mirror is minimized or full screen, and has no Dock icon.
- The waiting tray icon is white (black in light mode on macOS) to match the other icons; it follows light/dark changes while running.

## Capabilities

### Modified Capabilities
- `sidebar`: docked on macOS too.
- `tray-menu`: the icon matches the system's icons; the menu stays responsive.

## Impact

`tray.py`, `watcher.py` (`phones()`), `sidebar.py` (`MacDock`), `icons.py`; pyobjc Cocoa and Quartz become explicit macOS dependencies (already installed with pystray).
