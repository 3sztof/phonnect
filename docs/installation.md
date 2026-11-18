# Installation

## The installer (recommended)

**macOS / Linux**, in a terminal:

```sh
curl -fsSL https://github.com/3sztof/phonnect/releases/latest/download/install.sh | sh
```

**Windows**, in PowerShell (no admin needed):

```powershell
irm https://github.com/3sztof/phonnect/releases/latest/download/install.ps1 | iex
```

It walks you through the setup:

1. **Shows the plan.** Which version it installs, every folder and entry it creates, and whether uv, scrcpy and adb are already there. It also shows the command to uninstall later. Nothing happens until you confirm.
2. **uv**, if it's missing. [uv](https://docs.astral.sh/uv/) installs Phonnect and the Python it needs, kept apart from any other Python on the computer. It shows the official uv install command and asks before running it.
3. **scrcpy and adb**, if they're missing. It shows the package-manager command and asks first:

   | | |
   |---|---|
   | Windows | `winget install --id Genymobile.scrcpy` (includes adb, installed for your user only) |
   | macOS | `brew install scrcpy` and `brew install --cask android-platform-tools` (needs [Homebrew](https://brew.sh)) |
   | Linux | `sudo apt-get install scrcpy adb`, `sudo pacman -S scrcpy android-tools`, … |

   Your package manager keeps them up to date, which is why they're not bundled. If you skip this step, Phonnect waits with a red icon until they're installed.
4. **Phonnect itself**, with `uv tool install`, then `phonnect doctor` to check everything, and `phonnect install` to set up start at login and the app menu entry and start the tray app.

### What goes where

| | Windows | macOS | Linux |
|---|---|---|---|
| App (its own Python environment) | `%APPDATA%\uv\tools\phonnect` | `~/.local/share/uv/tools/phonnect` | same as macOS |
| Commands `phonnect`, `phonnect-tray` | `%USERPROFILE%\.local\bin` | `~/.local/bin` | `~/.local/bin` |
| Settings, log, remembered phones | `%LOCALAPPDATA%\phonnect` | `~/Library/Application Support/phonnect` | `~/.config/phonnect`, `~/.local/state/phonnect` |
| Start at login | `shell:startup\Phonnect.lnk` | `~/Library/LaunchAgents/io.github.3sztof.phonnect.plist` | `~/.config/autostart/phonnect.desktop` |
| App menu entry | Start menu: `Phonnect` | `~/Applications/Phonnect.app` (Spotlight, Launchpad) | `~/.local/share/applications/phonnect.desktop` |

The installer prints the real paths for your computer (uv's folders can be configured).

### Options

Pass options after `sh -s --` on macOS / Linux, e.g. `curl -fsSL …/install.sh | sh -s -- --yes`. On Windows, set environment variables before `irm … | iex`, e.g. `$env:PHONNECT_YES = "1"`.

| macOS / Linux | Windows | |
|---|---|---|
| `--version X.Y.Z` | `PHONNECT_VERSION` | install that release instead of the latest |
| `--no-deps` | `PHONNECT_NO_DEPS=1` | don't offer to install scrcpy / adb |
| `--yes` | `PHONNECT_YES=1` | answer yes to every question (unattended installs) |
| `--update` | `PHONNECT_UPDATE=1` | only replace the app; keep start at login and settings as they are |
| `--source PATH` | `PHONNECT_SOURCE` | install from a clone, a wheel or a git URL |

**Prefer to read it first?** Download it, read it, then run it: `curl -fsSLO …/install.sh && less install.sh && sh install.sh`, or on Windows save `install.ps1`, then run `powershell -ExecutionPolicy Bypass -File install.ps1`. Every release also has [build provenance](https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations), so you can check a file came from this repository's release workflow: `gh attestation verify install.sh --repo 3sztof/phonnect`.

## Updating

The tray menu's **Check for updates** entry becomes **Update Phonnect to X.Y.Z** when there's a new release (it checks GitHub once a day; *Settings → Check for updates automatically* turns that off). One click runs that release's installer in update mode in a small terminal window, which closes by itself when it's done: it stops the app (phone settings it changed are put back), replaces it, and starts it again. Settings, remembered phones and start at login are kept. scrcpy and adb aren't updated by Phonnect: *Check for updates* tells you when there's a newer scrcpy and which command updates it.

From a terminal: `phonnect update` (or `phonnect update --check` to only check).

## Uninstalling

```sh
curl -fsSL https://github.com/3sztof/phonnect/releases/latest/download/uninstall.sh | sh
```

```powershell
irm https://github.com/3sztof/phonnect/releases/latest/download/uninstall.ps1 | iex
```

It lists what it will remove and asks before deleting your settings and remembered phones (keep them if you might reinstall). It stops the app first, so phone settings it changed are put back. It doesn't remove uv, scrcpy or adb, and shows how to remove them if you want.

By hand: `phonnect uninstall --purge`, then `uv tool uninstall phonnect`.

The app isn't listed under Windows *Installed apps*, because uv manages it rather than a Windows installer.

## By hand, with uv

```sh
uv tool install --force --python ">=3.11" https://github.com/3sztof/phonnect/releases/download/vX.Y.Z/phonnect-X.Y.Z-py3-none-any.whl
phonnect install
```

Each [release](https://github.com/3sztof/phonnect/releases) lists its exact command. `phonnect install` enables start at login, adds the app menu entry and starts the tray app. Run `phonnect doctor` to check that scrcpy, adb and the tray work, and that your phone is detected.

## From a clone

```sh
git clone https://github.com/3sztof/phonnect
cd phonnect
just install
```

`just install` runs the same installer with `--source` pointing at the checkout. [just](https://github.com/casey/just) is available as `uv tool install rust-just`, `winget install Casey.Just` or `brew install just`.

## Starting and stopping

It starts by itself at login. To start it by hand, use the **Phonnect** entry in the Start menu, Spotlight or app launcher, or run `phonnect start`. Only one copy runs, so starting it again does nothing.

Quit from the tray menu, or run `phonnect stop`. Open mirror windows stay open.

## Migrating from older versions

- **scrcpy-autolaunch** (Phonnect's old name): just install Phonnect. The installer removes the old app and its entries, and moves its settings and remembered phones over.
- **The PowerShell version** from the `legacy-windows` branch: remove it first, or you'll get two windows.
  1. End the `powershell.exe` process whose command line contains `scrcpy-auto.ps1`.
  2. Delete `shell:startup\scrcpy-auto-launch.vbs`.
  3. Delete `%USERPROFILE%\scrcpy-auto\`.

  `phonnect doctor` warns you if the old Startup entry is still there.
