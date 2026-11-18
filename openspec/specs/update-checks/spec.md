# update-checks Specification

## Purpose
Tell the user when Phonnect or scrcpy has a new release, without sending anything but a daily request to GitHub, and let them update Phonnect from the tray menu or the command line.

## Requirements

### Requirement: Daily update check
When update checks are on (the default), the app SHALL ask GitHub for the latest Phonnect and scrcpy releases at most once a day, and MUST NOT send anything other than that request. A failed check SHALL keep the last known result and be retried later.

#### Scenario: Checked recently
- **WHEN** the last successful check is less than a day old
- **THEN** no request is made and the cached result is used

#### Scenario: Offline
- **WHEN** GitHub can't be reached
- **THEN** nothing is shown to the user, the previous result is kept, and the next check tries again

#### Scenario: Turned off
- **WHEN** the user turns off Check for updates
- **THEN** no requests are made and no update entries are shown

### Requirement: Update Phonnect from the menu
When a newer Phonnect release exists, the user SHALL be able to install it from the tray menu or with `phonnect update`. The update SHALL run that release's installer visibly in a terminal, ask before changing anything, put phone settings back before stopping the app, and keep settings, remembered phones and start at login.

#### Scenario: Update available
- **WHEN** a newer release exists and the user clicks Update Phonnect
- **THEN** a terminal window shows the installed and new version, asks to continue, then replaces the app and starts the new one

#### Scenario: Up to date
- **WHEN** the user runs `phonnect update` and the latest release is installed
- **THEN** it says so and changes nothing

### Requirement: scrcpy updates are explained, not installed
When a newer scrcpy release exists, the app SHALL say so and show how to update it for the way it was installed, and MUST NOT update scrcpy itself.

#### Scenario: scrcpy from winget
- **WHEN** scrcpy was installed with winget and a newer version exists
- **THEN** the menu entry explains to run `winget upgrade Genymobile.scrcpy` after closing the mirror windows
