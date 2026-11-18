# Installation

## Requirements

- **scrcpy and adb.** scrcpy 2.0 or newer is recommended; some features need newer versions (see [usage.md](usage.md)). They're **not bundled**: install them with your OS's package manager, which also keeps them up to date.

  | | |
  |---|---|
  | Windows | `winget install Genymobile.scrcpy` (includes adb) |
  | macOS | `brew install scrcpy && brew install --cask android-platform-tools` |
  | Linux | `sudo apt install scrcpy adb`, or your distro's equivalent |

- **[uv](https://docs.astral.sh/uv/)** installs the app, its Python dependencies (`pystray`, `Pillow`) and, if needed, Python 3.11+ itself.
- **[just](https://github.com/casey/just)** is optional, and only needed for installing from a clone: `uv tool install rust-just`, `winget install Casey.Just` or `brew install just`.

## From a release (recommended)

Every [release](https://github.com/3sztof/phonnect/releases) shows its install command:

```sh
uv tool install --force --python ">=3.11" https://github.com/3sztof/phonnect/releases/download/vX.Y.Z/phonnect-X.Y.Z-py3-none-any.whl
phonnect install
```

`phonnect install`:
- enables start at login
- adds an app menu entry (Start menu on Windows, app launcher on Linux)
- starts the tray app

Run `phonnect doctor` to check that scrcpy, adb and the tray work, and that your phone is detected.

## From a clone

```sh
git clone https://github.com/3sztof/phonnect
cd phonnect
just install
```

`just install`:
1. Checks for uv. If it's missing, it shows the official install command and asks before running it.
2. Installs the app from the checkout with `uv tool install`.
3. Runs `phonnect doctor`.
4. Runs `phonnect install`.

To install straight from `main` without cloning:

```sh
uv tool install --python ">=3.11" git+https://github.com/3sztof/phonnect
phonnect install
```

## Upgrading

```sh
phonnect stop
uv tool install --force --python ">=3.11" <wheel URL of the new release>
phonnect start
```

From a clone: `git pull`, then `just install`. Settings and remembered phones are kept either way.

## Starting and stopping

It starts by itself at login. To start it by hand, use the **phonnect** entry in the Start menu or app launcher, or run `phonnect start`. Only one copy runs, so starting it again does nothing.

Quit from the tray menu, or run `phonnect stop`. Open mirror windows stay open.

## Uninstalling

```sh
phonnect uninstall --purge
uv tool uninstall phonnect
```

`uninstall --purge` stops the app, removes the start-at-login and app menu entries, and deletes settings, logs and remembered phones. From a clone, `just uninstall` does all of it. scrcpy and adb are not touched.

The app isn't listed under Windows "Installed apps", because uv manages it rather than a Windows installer.

## Migrating from the legacy version

If you installed the PowerShell version from the `legacy-windows` branch, remove it first, or you'll get two windows:

1. End the `powershell.exe` process whose command line contains `scrcpy-auto.ps1`.
2. Delete `shell:startup\scrcpy-auto-launch.vbs`.
3. Delete `%USERPROFILE%\scrcpy-auto\`.

`phonnect doctor` warns you if the old Startup entry is still there.
