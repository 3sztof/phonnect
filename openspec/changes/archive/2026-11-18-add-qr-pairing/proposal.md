# Proposal

## Why

Pairing over Wi-Fi meant reading an IP address, a port and a 6-digit code off the phone and typing them into the PC. Android 11+ can pair by scanning a QR code instead ("Pair device with QR code"), which is quicker and harder to get wrong. Separately, the port scan used to find a phone's new port can hit another device if the phone's old IP was reassigned, which some networks treat as an attack.

## What Changes

- The pairing window shows a QR code next to the typed-code form. After the phone scans it, the phone advertises a pairing service with the name from the code over mDNS; the app finds it, pairs with the password from the code, remembers the phone and connects. The typed code stays as the alternative for networks without mDNS.
- `phonnect pair --qr` shows the QR code in the terminal.
- New setting **Find a Wi-Fi phone's new port by scanning it** (`wifi_port_scan`, on by default) to turn the scan off; docs explain when to.
- New dependency: segno (QR codes; BSD-3-Clause, pure Python, no dependencies).

## Capabilities

### Modified Capabilities
- `wireless`: pairing with a QR code; the port scan can be turned off.

## Impact

`wireless.py` (QR pairing, shared pair-and-connect), `dialogs.py`, `cli.py`, tray settings, `config.py`, docs/wifi.md, tests.
