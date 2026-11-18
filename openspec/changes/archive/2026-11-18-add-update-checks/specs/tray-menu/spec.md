# Spec Delta

## ADDED Requirements

### Requirement: Update entries
The tray menu SHALL show an Update Phonnect entry only when a newer Phonnect release exists, a scrcpy entry only when a newer scrcpy exists, and the installed Phonnect version in the Settings menu.

#### Scenario: New release
- **WHEN** the daily check finds a newer Phonnect release
- **THEN** "Update Phonnect to X.Y.Z…" appears above Quit, and the icon's tooltip mentions it

#### Scenario: No update
- **WHEN** everything is up to date
- **THEN** no update entries are shown
