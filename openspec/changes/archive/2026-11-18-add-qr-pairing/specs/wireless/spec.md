# Spec Delta

## MODIFIED Requirements

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
