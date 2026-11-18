# Spec Delta

## MODIFIED Requirements

### Requirement: Update Phonnect from the menu
When a newer Phonnect release exists, the user SHALL be able to install it with one click in the tray menu, or with `phonnect update`. The update SHALL run that release's installer visibly in a terminal, put phone settings back before stopping the app, and keep settings, remembered phones and start at login. From the menu, the click is the confirmation; `phonnect update` asks in the terminal.

#### Scenario: Update available
- **WHEN** a newer release exists and the user clicks Update Phonnect
- **THEN** a terminal window replaces the app and starts the new one without further questions, and closes by itself a few seconds after it worked

#### Scenario: Update fails
- **WHEN** the update can't be completed (for example no network)
- **THEN** the terminal window stays open with the error, and the previous version can still be started

#### Scenario: Up to date
- **WHEN** the user runs `phonnect update` and the latest release is installed
- **THEN** it says so and changes nothing

### Requirement: scrcpy updates are explained, not installed
When a newer scrcpy release exists, the result of Check for updates SHALL say so and show how to update it for the way it was installed. The app MUST NOT update scrcpy itself, and MUST NOT give scrcpy updates their own menu entry.

#### Scenario: scrcpy from winget
- **WHEN** scrcpy was installed with winget, a newer version exists, and the user clicks Check for updates
- **THEN** the result explains to run `winget upgrade Genymobile.scrcpy` after closing the mirror windows
