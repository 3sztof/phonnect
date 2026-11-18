# audio-and-input Specification

## Purpose

Where the phone's sound goes while mirroring, and how typing on the computer reaches the phone.

## Requirements

### Requirement: Sound stays on the phone by default
By default the app MUST NOT capture the phone's audio, so sound keeps playing on the phone and its Bluetooth devices (speakers, headphones, amps). Bluetooth itself MUST NOT be touched.

#### Scenario: Default
- **WHEN** a phone playing to a Bluetooth amp is mirrored with default settings
- **THEN** the sound keeps playing on the amp

### Requirement: Selectable audio mode
The user SHALL be able to choose: Off (default), PC and phone (sound also plays on the computer while the phone keeps playing; Android 13+, scrcpy 2.6+), or PC only (sound moves to the computer).

#### Scenario: Changing while mirroring
- **WHEN** the user changes the audio mode while a window is open
- **THEN** the window is reopened with the new mode

#### Scenario: PC and phone unsupported
- **WHEN** "PC and phone" is chosen but scrcpy is older than 2.6
- **THEN** sound stays on the phone and the reason is logged

### Requirement: Hide the phone's on-screen keyboard
With "Hide phone keyboard while mirroring" on (the default), typing on the computer SHALL reach the phone as a physical keyboard, so the on-screen keyboard stays hidden. Nothing SHALL change on the phone permanently.

#### Scenario: Typing in a text field
- **WHEN** the user focuses a text field on the phone through the mirror window
- **THEN** the on-screen keyboard doesn't cover the screen, and typing on the PC enters text
