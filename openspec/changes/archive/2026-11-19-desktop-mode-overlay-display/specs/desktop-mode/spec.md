# Spec Delta

## MODIFIED Requirements

### Requirement: Open the phone's desktop in its own window
The app SHALL open the phone's desktop on a second screen of a configurable size and density, shown in its own window, on which apps can be opened from the desktop's taskbar and app drawer. By default it SHALL use Android's simulated second screen, saving the phone's setting first and restoring it when the desktop window closes, the app quits, or the phone reconnects. If the simulated screen doesn't appear, it SHALL fall back to scrcpy's virtual screen. The user SHALL be told that the phone shows a preview of the desktop while it's open.

#### Scenario: Open from the sidebar
- **WHEN** the user presses Desktop mode in the sidebar or the tray
- **THEN** a separate window opens with the phone's desktop (taskbar, app drawer, large-screen layouts where Android provides them)

#### Scenario: Launching an app
- **WHEN** the user clicks an app in the desktop's taskbar on a Pixel with Android 16 or 17
- **THEN** the app opens in a window on the desktop

#### Scenario: Closed
- **WHEN** the user closes the desktop window
- **THEN** the simulated second screen is removed from the phone, and its setting is as before

#### Scenario: Already open
- **WHEN** the user opens desktop mode while it's already open for that phone
- **THEN** the existing window is brought to the front instead of opening a second one

#### Scenario: Simulated screen unavailable
- **WHEN** the simulated second screen doesn't appear within a few seconds
- **THEN** the setting is put back and desktop mode opens on scrcpy's virtual screen instead
