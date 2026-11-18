# auto-launch Specification

## Purpose

Open an scrcpy mirror window automatically when an Android phone connects, without opening it again behind the user's back after they close it.

## Requirements

### Requirement: Launch on USB connect
The app SHALL open a mirror window when a phone with authorized USB debugging connects over USB and "Auto-launch on USB" is on (the default).

#### Scenario: Phone plugged in
- **WHEN** an authorized phone is plugged in over USB and auto-launch on USB is on
- **THEN** a mirror window for that phone opens within a few seconds

#### Scenario: Auto-launch on USB is off
- **WHEN** an authorized phone is plugged in and auto-launch on USB is off
- **THEN** no window opens, and the phone is offered in the tray menu instead

#### Scenario: Authorization arrives later
- **WHEN** a phone first appears as unauthorized and the user then allows USB debugging on it
- **THEN** exactly one mirror window opens once the phone becomes authorized

### Requirement: Launch on Wi-Fi connect is opt-in
The app SHALL open a mirror window for a phone connecting over Wi-Fi only when "Auto-launch on Wi-Fi" is on; it is off by default.

#### Scenario: Wi-Fi auto-launch off
- **WHEN** a paired phone connects over Wi-Fi and auto-launch on Wi-Fi is off
- **THEN** no window opens

#### Scenario: Wi-Fi auto-launch on
- **WHEN** a paired phone connects over Wi-Fi and auto-launch on Wi-Fi is on
- **THEN** a mirror window opens, using the lower Wi-Fi resolution and bitrate settings

### Requirement: Closing the window keeps it closed
The app MUST NOT reopen a window the user closed while the phone stays connected. It SHALL open again only after the phone disconnects and reconnects, or when the user asks for it.

#### Scenario: Window closed, phone still plugged in
- **WHEN** the user closes the mirror window and the phone stays connected
- **THEN** no new window opens

#### Scenario: Replug after closing
- **WHEN** the user closes the window, unplugs the phone and plugs it back in
- **THEN** a new window opens

#### Scenario: adb reconnects a closed phone on its own
- **WHEN** the user closed a Wi-Fi phone's window and adb later reconnects that phone by itself
- **THEN** no window opens until the user clicks the phone or plugs it in over USB

### Requirement: Closing a Wi-Fi window ends the Wi-Fi connection
When the user closes a Wi-Fi mirror window (or stops it from the tray), the app SHALL disconnect that phone's Wi-Fi debugging connection, unless "Keep Wi-Fi connected after closing the window" is on.

#### Scenario: Default behavior
- **WHEN** the user closes a Wi-Fi mirror window
- **THEN** the phone's Wi-Fi debugging connection is disconnected after any temporary phone settings have been restored

#### Scenario: Keep connected
- **WHEN** "Keep Wi-Fi connected after closing the window" is on and the user closes a Wi-Fi window
- **THEN** the phone stays connected

#### Scenario: Lost connection is not a close
- **WHEN** a Wi-Fi window ends because the connection dropped or scrcpy failed
- **THEN** the app does not treat it as closed by the user

### Requirement: One window per phone
The app SHALL mirror each physical phone in at most one window, recognizing the same phone over USB and Wi-Fi, and SHALL prefer USB.

#### Scenario: Phone on USB and Wi-Fi
- **WHEN** the same phone is connected over USB and Wi-Fi at the same time
- **THEN** exactly one mirror window opens, over USB

### Requirement: Start failures are reported
The app SHALL tell the user when scrcpy fails right after starting, and point to the log.

#### Scenario: scrcpy exits with an error immediately
- **WHEN** scrcpy exits with a non-zero code within a few seconds of starting
- **THEN** the user is notified that mirroring failed, with a pointer to the log

### Requirement: Explain why a phone isn't detected
The app SHALL explain, in the tray and in `doctor`, when a phone can't be mirrored for a reason the user can fix on the phone.

#### Scenario: Unauthorized
- **WHEN** a phone is connected but USB debugging isn't authorized yet
- **THEN** the tray shows that the user has to allow USB debugging on the phone

#### Scenario: USB debugging switched off
- **WHEN** a phone is reachable over Wi-Fi but reports USB debugging as off
- **THEN** the app warns once that plugging it in won't open a window, and how to turn USB debugging on
