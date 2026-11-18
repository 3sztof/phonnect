# Spec Delta

## ADDED Requirements

### Requirement: Windows reopen where they were
On Windows, with Reopen windows where they were on (the default), each phone's mirror window SHALL reopen at the position and height it last had, separately for portrait and landscape, and the desktop-mode window at its own last position and height. Position and size in the user's own scrcpy arguments SHALL take precedence.

#### Scenario: Reopened
- **WHEN** the user moved and resized a phone's window, closed it, and the phone connects again
- **THEN** the window opens at the same place and height

#### Scenario: Monitor gone
- **WHEN** the remembered position is on a monitor that's no longer connected
- **THEN** the window opens at scrcpy's default position, with the remembered height

#### Scenario: Turned off
- **WHEN** the user turns off Reopen windows where they were
- **THEN** windows open where and how scrcpy places them

### Requirement: No black bars
A mirror window SHALL match the shape of the phone's picture. When it opens wider or narrower than the picture (scrcpy's first guess, or after a rotation), the app SHALL resize it to fit once the picture size is known, keeping its height.

#### Scenario: First open on a wide screen
- **WHEN** a phone is mirrored for the first time on a 3440x1440 screen and scrcpy's window has black bars at the sides
- **THEN** within a second or two the window narrows to fit the picture, and that size is remembered
