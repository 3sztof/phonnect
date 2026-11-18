# wireless Specification

## Purpose

Mirror phones over Wi-Fi (Android 11+ wireless debugging): pair once, then connect with a click even though Android changes the debugging port.

## Requirements

### Requirement: Pair from the app
The app SHALL let the user pair a phone by scanning a QR code shown on the PC, or by entering the IP address, port and code shown on the phone, and SHALL connect to it right after pairing. Each QR code SHALL use a newly generated name and password.

#### Scenario: Pairing with the QR code
- **WHEN** the user opens Pair new phone and scans the code with "Pair device with QR code" on the phone
- **THEN** the app finds the phone over mDNS, pairs, remembers it and connects, without the user typing anything

#### Scenario: Successful pairing
- **WHEN** the user enters a valid pairing address and code
- **THEN** the phone is paired, remembered, and connected if its debugging port can be found

#### Scenario: Wrong code
- **WHEN** pairing fails
- **THEN** the error is shown in the pairing window, not only as a notification

#### Scenario: The phone never shows up
- **WHEN** no phone scans the code within 5 minutes, for example because mDNS is blocked
- **THEN** the window says the code expired, and pairing with a typed code still works

### Requirement: Remember phones
The app SHALL remember every phone it has seen (name, last Wi-Fi IP, last working address), learning the IP over USB too, and SHALL list phones adb has paired with even if the app never saw them.

#### Scenario: Seen over USB first
- **WHEN** a phone was connected over USB before
- **THEN** its Wi-Fi IP is known, so the app can find it over Wi-Fi later

### Requirement: Reconnect despite port changes
Connecting to a remembered phone SHALL try, in order: the port advertised over mDNS, the last address that worked, and, unless the user turned it off, a scan of the phone's IP for the new port.

#### Scenario: Port changed after a reboot
- **WHEN** the phone's debugging port has changed and mDNS is blocked on the network
- **THEN** the app finds the new port by scanning the phone's IP and connects, typically within 15 seconds

#### Scenario: Scan turned off
- **WHEN** the user turned off the port scan and mDNS and the last address fail
- **THEN** no ports are probed, and the result says the scan is turned off

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
