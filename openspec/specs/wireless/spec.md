# wireless Specification

## Purpose

Mirror phones over Wi-Fi (Android 11+ wireless debugging): pair once, then connect with a click even though Android changes the debugging port.

## Requirements

### Requirement: Pair from the app
The app SHALL let the user pair a phone by entering the IP address, port and code shown on the phone, and SHALL connect to it right after pairing.

#### Scenario: Successful pairing
- **WHEN** the user enters a valid pairing address and code
- **THEN** the phone is paired, remembered, and connected if its debugging port can be found

#### Scenario: Wrong code
- **WHEN** pairing fails
- **THEN** the error is shown in the pairing window, not only as a notification

### Requirement: Remember phones
The app SHALL remember every phone it has seen (name, last Wi-Fi IP, last working address), learning the IP over USB too, and SHALL list phones adb has paired with even if the app never saw them.

#### Scenario: Seen over USB first
- **WHEN** a phone was connected over USB before
- **THEN** its Wi-Fi IP is known, so the app can find it over Wi-Fi later

### Requirement: Reconnect despite port changes
Connecting to a remembered phone SHALL try, in order: the port advertised over mDNS, the last address that worked, and a scan of the phone's IP for the new port.

#### Scenario: Port changed after a reboot
- **WHEN** the phone's debugging port has changed and mDNS is blocked on the network
- **THEN** the app finds the new port by scanning the phone's IP and connects, typically within 15 seconds

#### Scenario: Wireless debugging is off
- **WHEN** none of the attempts succeed
- **THEN** the user sees what was tried and what to check on the phone

### Requirement: Only usable connections count
A connection SHALL count as successful only once the phone is online; stale "offline" entries SHALL be cleared before connecting.

#### Scenario: Wrong port entered
- **WHEN** the user connects to an address that adb accepts but the phone never comes online
- **THEN** the attempt is reported as failed, and the stale entry is removed

### Requirement: Manage Wi-Fi phones window
The app SHALL provide a window listing remembered phones with their status, with connect, disconnect, pair and connect-to-address actions, showing results inline.

#### Scenario: Connect from the window
- **WHEN** the user selects a phone and clicks Connect
- **THEN** progress and the result appear in the window
