# Security policy

## Reporting a vulnerability

Please report security problems privately, not in a public issue:
**[Report a vulnerability](https://github.com/3sztof/phonnect/security/advisories/new)** (GitHub's private reporting).

Include what you found, how to reproduce it, and the Phonnect version (`phonnect --version`).
You'll get an answer within a week. Fixes are released as soon as they're ready, and you're credited unless you'd rather not be.

## Supported versions

Only the latest release gets fixes. Update with **Update Phonnect** in the tray menu, or `phonnect update`.

## What Phonnect does, security-wise

- It runs as your user. It never needs admin rights and never changes system settings.
- The tray app accepts commands from its own helper windows over `127.0.0.1` only, with a random token kept in a file only your user can read.
- It talks to phones only through `adb` and `scrcpy`, which you install yourself. Settings it changes on a phone are saved first and put back afterwards.
- Network access: GitHub's API, once a day, to check for updates (can be turned off). When reconnecting to a Wi-Fi phone, optionally a scan of that phone's last known IP for its debugging port (can be turned off too).
- Releases are built by GitHub Actions from a tagged commit, with [build provenance](https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations): `gh attestation verify <file> --repo 3sztof/phonnect`.
