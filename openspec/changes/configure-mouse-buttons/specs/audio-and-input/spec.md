# Spec Delta

## ADDED Requirements

### Requirement: Mouse buttons are configurable
Each secondary mouse button (right, middle, side back, side forward) SHALL do what the user chose: send the click to the app, trigger a phone action (Back, Home, Recent apps, Notifications), or nothing. Holding Shift SHALL give the phone actions Back, Home, Recent apps and Notifications respectively.

#### Scenario: Default right click
- **WHEN** the user right-clicks in the mirror window with default settings
- **THEN** the click is sent to the app, and the phone does not go back

#### Scenario: Default side buttons
- **WHEN** the user presses the mouse's side "back" button
- **THEN** the phone goes back

#### Scenario: Shift for the original shortcuts
- **WHEN** the user holds Shift and right-clicks
- **THEN** the phone goes back

#### Scenario: Changed while mirroring
- **WHEN** the user changes a mouse button's action while a mirror window is open
- **THEN** the window is reopened with the new binding

#### Scenario: Old scrcpy
- **WHEN** the installed scrcpy doesn't support mouse bindings (older than 2.5)
- **THEN** scrcpy's own default behavior is used and mirroring still works
