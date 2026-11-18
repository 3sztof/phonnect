# Tasks

- [x] `updates.py`: latest release from GitHub's API, version comparison, daily cache in the state folder
- [x] Tray: background check (30 s after start, then hourly; the cache limits requests to one a day), update entries, tooltip line, settings toggle, "Check for updates now", version in Settings
- [x] Update Phonnect: open a terminal running the release's installer in update mode (`PHONNECT_UPDATE=1` / `--update`)
- [x] scrcpy: explain how to update for winget, scoop, Chocolatey, Homebrew, snap or a download
- [x] `phonnect update [--check]` (Windows: continues in a new window, because the running command's files are replaced)
- [x] `check_updates` setting, docs (usage, installation), tests with the network faked
