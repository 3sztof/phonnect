# Spec Delta

## MODIFIED Requirements

### Requirement: Status icon
The tray icon SHALL show whether a phone is connected, and SHALL show a problem state when scrcpy or adb can't be found. Its outline SHALL match the other icons in the tray or menu bar (white on dark, dark on light) and follow light/dark changes while running.

#### Scenario: States
- **WHEN** no phone is connected, a phone is connected, or scrcpy/adb is missing
- **THEN** the icon shows waiting, connected (green phone) or problem (red phone) respectively

#### Scenario: Dark menu bar on macOS
- **WHEN** macOS is in dark mode
- **THEN** the waiting icon is white like the other menu bar icons

## ADDED Requirements

### Requirement: The menu stays responsive
Changes reported by the watcher (a phone connecting, a window closing) MUST NOT freeze the tray. On macOS, the menu and icon SHALL only be updated from the main thread.

#### Scenario: Closing the mirror window on macOS
- **WHEN** the user closes a mirror window
- **THEN** the phone's settings are put back and the menu updates, and the menu bar icon can still be clicked
