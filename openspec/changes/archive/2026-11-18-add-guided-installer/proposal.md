# Proposal

## Why

Installing took several steps: install scrcpy + adb, install uv, copy a long `uv tool install <wheel URL>` command from the release page, run `phonnect install`. Modern tools install with one line (`curl -fsSL … | sh`), but the user should still see what gets installed, where, and how to remove it. Also: on macOS Phonnect had no app entry (not in Spotlight or Launchpad), and on Windows its entries were named in lowercase.

## What Changes

- `install.sh` (macOS, Linux) and `install.ps1` (Windows), attached to every release and run with `curl -fsSL …/releases/latest/download/install.sh | sh` or `irm …/install.ps1 | iex`. They show the plan (version, every folder and entry, what's already installed, how to uninstall), ask before doing anything, ask separately before installing uv and before installing scrcpy + adb with the package manager (winget, Homebrew, apt, pacman, zypper, dnf), then install Phonnect, run `doctor` and `install`.
- `uninstall.sh` / `uninstall.ps1`: list what they remove, ask whether to keep settings, stop the app (phone settings are put back), remove it, and explain how to remove uv, scrcpy and adb if wanted.
- Options: `--version`, `--no-deps`, `--yes`, `--update`, `--source` (Windows: environment variables, because `irm | iex` can't pass arguments). Each release's copy installs that release.
- macOS: `~/Applications/Phonnect.app`, a minimal app bundle (no Dock icon) that starts the tray, so Phonnect is in Spotlight, Launchpad and Finder.
- Windows: the Start menu and Startup entries are named "Phonnect". Entries are rewritten once after each update, so existing installs get the new names and paths.
- Release workflow: build and tests with a read-only token, a separate publish job, build provenance for every file, release notes with the one-line installers.

## Capabilities

### Modified Capabilities
- `installation`: one-line guided install and uninstall, macOS app entry, entry names, release contents.

## Impact

`scripts/install.*`, `scripts/uninstall.*`, `autostart.py`, `just install`, release workflow, README and docs/installation.md.
