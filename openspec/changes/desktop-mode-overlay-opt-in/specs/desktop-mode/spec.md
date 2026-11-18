# Spec Delta

## MODIFIED Requirements

### Requirement: Open the phone's desktop in its own window
The app SHALL open the phone's desktop on a second screen of a configurable size and density, in its own window. By default it SHALL use scrcpy's virtual screen, which changes nothing on the phone. Android's simulated second screen SHALL only be used when the user opts in (experimental), falling back to the virtual screen if it doesn't appear.

#### Scenario: Open from the sidebar
- **WHEN** the user presses Desktop mode in the sidebar or the tray
- **THEN** a separate window opens with the phone's desktop (taskbar, app drawer, large-screen layouts where Android provides them)

#### Scenario: Default leaves the phone alone
- **WHEN** the user opens desktop mode without opting in to the simulated second screen
- **THEN** no phone setting is changed, and nothing is shown on the phone's own screen

#### Scenario: Launching an app with the opt-in
- **WHEN** the user opted in and clicks an app in the desktop's taskbar on a Pixel with Android 16 or 17
- **THEN** the app opens in a window on the desktop

#### Scenario: Closed
- **WHEN** the user closes a desktop window that used the simulated second screen
- **THEN** the simulated second screen is removed from the phone, and its setting is as before

#### Scenario: Already open
- **WHEN** the user opens desktop mode while it's already open for that phone
- **THEN** the existing window is brought to the front instead of opening a second one

#### Scenario: Simulated screen unavailable
- **WHEN** the simulated second screen doesn't appear within a few seconds
- **THEN** the setting is put back and desktop mode opens on scrcpy's virtual screen instead
