# installation Specification

## Purpose

Installing, starting, updating and removing the app, on Windows, macOS and Linux, without admin rights and without leaving anything behind.

## Requirements

### Requirement: Simple install, dependencies separate
The app SHALL install with one command per OS (`curl … | sh` on macOS and Linux, `irm … | iex` in PowerShell on Windows) that walks the user through the setup, and also with uv directly or from a clone with `just install`. scrcpy and adb SHALL come from the OS package manager and MUST NOT be bundled.

#### Scenario: The plan comes first
- **WHEN** the user runs the installer
- **THEN** it shows the version, every folder and entry it will create, which of uv, scrcpy and adb are already installed, and how to uninstall, and changes nothing until the user confirms

#### Scenario: scrcpy missing
- **WHEN** scrcpy or adb isn't found
- **THEN** the installer shows the package-manager command and asks before running it; `doctor` and the tray also say so and show the install command for the OS

#### Scenario: uv missing during `just install`
- **WHEN** uv isn't installed (one-line installer or `just install`)
- **THEN** the installer shows the official install command and asks before running it

#### Scenario: Unattended install
- **WHEN** the installer runs with `--yes` (or `PHONNECT_YES=1`)
- **THEN** it answers yes to every question, and fails clearly instead of waiting if it has no terminal to ask

#### Scenario: Uninstall
- **WHEN** the user runs the uninstaller
- **THEN** it lists what it removes, asks whether to keep settings and remembered phones, puts phone settings back by stopping the app, and leaves uv, scrcpy and adb installed

### Requirement: Starts at login, no admin rights
`install` SHALL register a per-user start-at-login entry and an app menu entry named "Phonnect" (Start menu on Windows, `~/Applications/Phonnect.app` on macOS, app launcher on Linux), with no admin rights. After an update, existing entries SHALL be rewritten once so they point at the new install.

#### Scenario: After install
- **WHEN** the user runs `phonnect install`
- **THEN** the app starts now, again at every login, and can be started from the Start menu, Spotlight or the app launcher

#### Scenario: Found in Spotlight
- **WHEN** Phonnect is installed on macOS
- **THEN** searching "Phonnect" in Spotlight finds the app, which starts the tray without a Dock icon

#### Scenario: Entry from an older version
- **WHEN** an entry made by an older version exists (for example `phonnect.lnk`)
- **THEN** the first start of the new version replaces it with the current one (`Phonnect.lnk`)

### Requirement: Single instance
Only one instance SHALL run per user; starting it again SHALL do nothing.

#### Scenario: Started twice
- **WHEN** the app is started while it's already running
- **THEN** the second start exits without opening another tray icon

### Requirement: Clean stop and uninstall
`stop` SHALL ask the running app to quit cleanly (restoring phone settings). `uninstall --purge` SHALL remove the start-at-login and menu entries, settings, logs and remembered phones, leaving scrcpy and adb alone.

#### Scenario: Uninstall
- **WHEN** the user runs `just uninstall`
- **THEN** nothing of the app is left except scrcpy, adb and uv

### Requirement: Bounded log
The app SHALL keep a timestamped log of device and window events, capped at about 2 MB.

#### Scenario: Long-running use
- **WHEN** the app runs for months
- **THEN** the log never grows beyond about 2 MB

### Requirement: Versioned releases
Each release SHALL be built by CI from a version tag that matches the package version, with tests and build running without write access, and published as a GitHub Release with the wheel, the source archive, the installer and uninstaller scripts (set to install that release), and build provenance for each file.

#### Scenario: Tag doesn't match
- **WHEN** a tag is pushed that doesn't match the package version
- **THEN** the release workflow fails without publishing

#### Scenario: Verifying a download
- **WHEN** a user runs `gh attestation verify <file> --repo 3sztof/phonnect` on a release file
- **THEN** it confirms the file was built by the release workflow
