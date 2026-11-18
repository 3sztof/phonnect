# phone-settings Specification

## Purpose

Settings the app changes on the phone while it's mirrored (screen rotation, content size), with the guarantee that the phone always gets its own settings back.

## Requirements

### Requirement: Changes are temporary and always restored
Before changing a phone setting, the app SHALL save the phone's own value, and SHALL restore it when the window closes, the setting is switched back, or the app quits. The saved value SHALL survive app restarts.

#### Scenario: Window closed
- **WHEN** a window with a changed phone setting is closed
- **THEN** the phone's own value is restored

#### Scenario: Phone unplugged mid-session
- **WHEN** the phone disconnects while a setting is changed, so it can't be restored right away
- **THEN** the saved value is restored the next time that phone connects

#### Scenario: Repeated changes
- **WHEN** the same setting is changed several times during one session
- **THEN** the value restored at the end is the phone's original one, not an intermediate one

### Requirement: Force landscape
With Force landscape on, a mirrored phone SHALL be locked to landscape, including apps that request portrait. Turning it on or off SHALL apply to open windows immediately.

#### Scenario: Turned on while mirroring
- **WHEN** the user turns on Force landscape while a phone is mirrored
- **THEN** the phone rotates to landscape without the window being reopened

#### Scenario: Reopening a window keeps landscape
- **WHEN** a mirror window is reopened to apply another setting while Force landscape is on
- **THEN** the phone stays in landscape without rotating back in between

### Requirement: Content size
The content size SHALL be set as a percentage (50–100%) of the phone's own display size, lower values fitting more on screen. It SHALL apply on release of the slider, be remembered for the next window, and 100% SHALL restore the phone's own value.

#### Scenario: Custom display size on the phone
- **WHEN** the phone already uses a custom display size and the user sets 75%
- **THEN** the result is 75% of the user's own setting, not of the factory default

#### Scenario: Back to 100%
- **WHEN** the user moves the slider back to 100%
- **THEN** the phone's own display size is restored exactly
