# tray-menu Specification

## Purpose

A tray (menu bar) icon that shows the phones' state at a glance and puts the most common action, "show me this phone", one click away.

## Requirements

### Requirement: Phones first, one entry each
The menu SHALL list connected and remembered phones first, one entry per phone, each showing its state and connection type (USB, Wi-Fi or both).

#### Scenario: Several phones
- **WHEN** one phone is mirrored over USB and another paired phone isn't connected
- **THEN** the menu starts with the mirrored phone, followed by the other phone offered for connecting

#### Scenario: No phones yet
- **WHEN** no phone is connected or remembered
- **THEN** the menu says how to connect one and offers Wi-Fi pairing

### Requirement: Clicking a phone shows it
Clicking a phone that isn't mirrored SHALL open its mirror window, connecting over Wi-Fi first if needed, regardless of the auto-launch settings.

#### Scenario: Connected but not mirrored
- **WHEN** the user clicks a connected phone that has no window
- **THEN** its mirror window opens

#### Scenario: Remembered Wi-Fi phone
- **WHEN** the user clicks a remembered phone that isn't connected
- **THEN** the app connects to it over Wi-Fi and opens the mirror window, or shows why connecting failed

### Requirement: Actions for a mirrored phone
A mirrored phone's entry SHALL offer: show window (Windows), stop mirroring, open desktop mode, open shell, and disconnect Wi-Fi (when connected over Wi-Fi).

#### Scenario: Stop mirroring
- **WHEN** the user chooses "Stop mirroring"
- **THEN** the window closes, and it is handled like a window the user closed

### Requirement: Status icon
The tray icon SHALL show whether a phone is connected, and SHALL show a problem state when scrcpy or adb can't be found.

#### Scenario: States
- **WHEN** no phone is connected, a phone is connected, or scrcpy/adb is missing
- **THEN** the icon shows waiting, connected (green phone) or problem (red phone) respectively

### Requirement: Settings in submenus
Session settings (Audio, Force landscape) SHALL be top-level; set-once settings SHALL be grouped under a Settings submenu; Wi-Fi pairing and connecting SHALL be under a Wi-Fi submenu.

#### Scenario: Changing a setting
- **WHEN** the user changes a setting in the menu
- **THEN** it is saved immediately and kept across restarts

### Requirement: Left click opens the menu on Windows
On Windows, left-clicking the tray icon SHALL open the same menu as right-clicking.

#### Scenario: Left click
- **WHEN** the user left-clicks the tray icon on Windows
- **THEN** the menu opens

### Requirement: Quit restores phones
Quitting SHALL stop watching for phones, close the sidebars, and restore every phone setting the app changed. Open mirror windows SHALL stay open.

#### Scenario: Quit while mirroring in landscape
- **WHEN** the user quits while a phone is mirrored with Force landscape on
- **THEN** the phone's own rotation setting is restored, and the mirror window stays open
