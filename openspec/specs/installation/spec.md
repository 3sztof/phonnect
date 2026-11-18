# installation Specification

## Purpose

Installing, starting, updating and removing the app, on Windows, macOS and Linux, without admin rights and without leaving anything behind.

## Requirements

### Requirement: Simple install, dependencies separate
The app SHALL install with uv from a GitHub release (or a clone with `just install`), together with its Python dependencies. scrcpy and adb SHALL come from the OS package manager and MUST NOT be bundled.

#### Scenario: scrcpy missing
- **WHEN** scrcpy or adb isn't found
- **THEN** `doctor` and the tray say so and show the install command for the OS

#### Scenario: uv missing during `just install`
- **WHEN** uv isn't installed
- **THEN** the installer shows the official install command and asks before running it

### Requirement: Starts at login, no admin rights
`install` SHALL register a per-user start-at-login entry and an app menu entry (Start menu on Windows, app launcher on Linux), with no admin rights.

#### Scenario: After install
- **WHEN** the user runs `scrcpy-autolaunch install`
- **THEN** the app starts now, again at every login, and can be started from the Start menu

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
Each release SHALL be built by CI from a version tag that matches the package version, and published as a GitHub Release with the wheel, source archive and install command.

#### Scenario: Tag doesn't match
- **WHEN** a tag is pushed that doesn't match the package version
- **THEN** the release workflow fails without publishing
