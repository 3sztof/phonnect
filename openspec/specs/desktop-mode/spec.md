# desktop-mode Specification

## Purpose

Use the phone's desktop experience on the computer, like plugging it into a monitor, in a window separate from the phone mirror.

## Requirements

### Requirement: Open the phone's desktop in its own window
The app SHALL open the phone's desktop on a second screen of a configurable size and density, in its own window. By default it SHALL use scrcpy's virtual screen, which changes nothing on the phone. Android's simulated second screen SHALL only be used when the user opts in (experimental), falling back to the virtual screen if it doesn't appear.

#### Scenario: Open from the sidebar
- **WHEN** the user presses Desktop mode in the sidebar or the tray
- **THEN** a separate window opens with the phone's desktop (taskbar, app drawer, large-screen layouts where Android provides them)

#### Scenario: Default leaves the phone alone
- **WHEN** the user opens desktop mode without opting in to the simulated second screen
- **THEN** no phone setting is changed, and nothing is shown on the phone's own screen

#### Scenario: Launching an app
- **WHEN** the user opted in to the simulated second screen and clicks an app in the desktop's taskbar on a Pixel with Android 16 or 17
- **THEN** the app opens in a window on the desktop

#### Scenario: Warned before it opens
- **WHEN** the user opens desktop mode
- **THEN** a notification says it's experimental, and with the simulated second screen, how to remove its preview from the phone if it stays

#### Scenario: Closed
- **WHEN** the user closes a desktop window that used the simulated second screen
- **THEN** the simulated second screen is removed from the phone, and its setting is as before

#### Scenario: Already open
- **WHEN** the user opens desktop mode while it's already open for that phone
- **THEN** the existing window is brought to the front instead of opening a second one

#### Scenario: Simulated screen unavailable
- **WHEN** the simulated second screen doesn't appear within a few seconds
- **THEN** the setting is put back and desktop mode opens on scrcpy's virtual screen instead

### Requirement: The phone's setting is put back
The simulated second screen SHALL be a temporary, saved and restored phone setting: removed when the desktop window closes, when the app quits, or when the phone reconnects after being gone. The user SHALL be told that the phone shows a preview of the desktop while it's on.

#### Scenario: Preview explained
- **WHEN** desktop mode opens on the simulated second screen
- **THEN** a notification says the phone shows a preview until the desktop window is closed

#### Scenario: Quit with the desktop open
- **WHEN** the user quits Phonnect while a desktop window is open
- **THEN** the desktop window closes and the simulated second screen is removed

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
