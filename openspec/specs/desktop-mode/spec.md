# desktop-mode Specification

## Purpose

Use the phone's desktop experience on the computer, like plugging it into a monitor, in a window separate from the phone mirror.

## Requirements

### Requirement: Open the phone's desktop in its own window
The app SHALL open the phone's desktop on a second, virtual screen of a configurable size and density, shown in its own window, without changing the phone's screen or settings.

#### Scenario: Open from the sidebar
- **WHEN** the user presses Desktop mode in the sidebar or the tray
- **THEN** a separate window opens with the phone's desktop (taskbar, app drawer, large-screen layouts where Android provides them)

#### Scenario: Already open
- **WHEN** the user opens desktop mode while it's already open for that phone
- **THEN** the existing window is brought to the front instead of opening a second one

### Requirement: Doesn't disturb the mirror
Desktop mode SHALL NOT take the audio or change the main mirror window.

#### Scenario: Audio
- **WHEN** desktop mode is open alongside the mirror window
- **THEN** sound (if forwarded) stays with the mirror window

### Requirement: Clear when unsupported
The app SHALL say so when desktop mode can't be used (scrcpy older than 3.0, phone not connected).

#### Scenario: Old scrcpy
- **WHEN** the installed scrcpy is older than 3.0
- **THEN** the user is told desktop mode needs scrcpy 3.0 or newer
