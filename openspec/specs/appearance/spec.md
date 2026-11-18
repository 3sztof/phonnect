# appearance Specification

## Purpose

The app looks native on each OS, follows light and dark mode, and never shows stray console windows.

## Requirements

### Requirement: No console windows
On Windows, the app and everything it starts (adb, scrcpy, sidebars, dialogs) MUST NOT show console windows, except a terminal the user explicitly opens.

#### Scenario: Plugging in a phone
- **WHEN** a phone is plugged in and the mirror opens
- **THEN** only the mirror window (and its sidebar) appears

### Requirement: Follows the OS look and dark mode
The app's own windows SHALL use the OS's native style and follow its light or dark mode; on Windows this includes the title bars of the mirror and desktop windows. The tray menu SHALL follow the system mode.

#### Scenario: Windows in dark mode
- **WHEN** Windows is set to dark mode
- **THEN** the app's windows, the mirror window's title bar and the tray menu are dark

### Requirement: Recognizable icon
The app SHALL use its own icon for the tray, the Start menu / app launcher entry, and its windows, readable on light and dark taskbars.

#### Scenario: Light taskbar
- **WHEN** the taskbar uses the light theme
- **THEN** the tray icon is drawn dark so it stays visible
