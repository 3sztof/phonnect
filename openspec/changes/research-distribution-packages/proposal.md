# Proposal

## Why

Tracking issue: [#10](https://github.com/3sztof/scrcpy-autolaunch/issues/10).

Installing currently needs uv and a long command copied from the release page. `winget install scrcpy-autolaunch` (and Scoop, Homebrew) would be the most familiar install for most people, and would handle updates.

## What Changes

This is a research change: the outcome is a decision and a design, then a follow-up change to implement it.

- Compare the options:
  - A standalone build (PyInstaller or Nuitka). Doesn't need Python, but has antivirus false positives on Windows, needs signing/notarization on macOS, and needs one build per OS in CI.
  - Package manifests that install through uv (e.g. a Scoop/winget portable package that bootstraps uv), if the package managers' rules allow it.
  - Homebrew formula/tap for macOS and Linux.
- Check each package manager's submission rules, update flow and maintenance cost.
- Recommend one path; scrcpy and adb stay separate dependencies (declared as package dependencies where possible).

Out of scope: an auto-updater inside the app (see the update-checks change).

## Capabilities

### New Capabilities
<!-- decided after the research -->

### Modified Capabilities
- `installation`: may gain package-manager install paths.

## Impact

Release workflow, possibly new build tooling and manifests in separate repos (winget-pkgs, Scoop bucket, Homebrew tap), docs/installation.md.
