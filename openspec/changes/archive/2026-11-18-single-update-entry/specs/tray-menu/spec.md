# Spec Delta

## MODIFIED Requirements

### Requirement: Update entries
The tray menu SHALL have one updates entry: "Check for updates" normally, "Update Phonnect to X.Y.Z" when a newer Phonnect release exists. The installed Phonnect version SHALL be shown in the Settings menu.

#### Scenario: New release
- **WHEN** the daily check finds a newer Phonnect release
- **THEN** the entry above Quit reads "Update Phonnect to X.Y.Z", and the icon's tooltip mentions it

#### Scenario: No update
- **WHEN** everything is up to date
- **THEN** the entry reads "Check for updates", and clicking it reports that Phonnect is up to date
