# Development

```sh
git clone https://github.com/3sztof/scrcpy-autolaunch
cd scrcpy-autolaunch
just test       # unit tests
just dev-tray   # run the tray from the checkout
just dev-run    # console-only watcher from the checkout (Ctrl+C to stop)
just install    # install the checkout as the real app
```

## How it works

- **The watcher** (`watcher.py`) runs `adb devices -l` once a second. A phone that appears, or becomes authorized, gets a scrcpy window if auto-launch is on for its connection type.
- **Closing a window doesn't reopen it:** a phone only counts as new again after it disappears from adb.
- **One window per phone:** a phone on both USB and Wi-Fi is recognized by its hardware serial number (`ro.serialno`) and mirrored once, over USB.
- **One adb for everything:** scrcpy is started with `ADB` set to the same adb binary, so two adb versions don't keep restarting each other's server.
- **No console windows on Windows:** scrcpy and adb run with `CREATE_NO_WINDOW`. The tray starts through a windowless entry point (`scrcpy-autolaunch-tray`).
- **The tray** (`tray.py`, pystray) builds its menu from the watcher's phones plus the remembered ones.
- **The Wi-Fi windows** (`dialogs.py`, Tk) run in a separate process, because macOS needs the main thread for both Tk and the tray.
- **Wi-Fi** (`wireless.py`): remembered phones, the paired list from `~/.android/adb_known_hosts.pb`, and reconnecting via mDNS, then the last address, then a port scan.
- **Force landscape** (`rotation.py`): saves the phone's rotation settings to `rotation.json`, locks to landscape with `cmd window user-rotation`, and restores afterwards. One worker thread runs these changes, so they never race.
- **Start at login and app menu entries** (`autostart.py`): a Startup folder shortcut (Windows), a LaunchAgent (macOS), and XDG autostart and `.desktop` files (Linux).
- **One instance only** (`instance.py`): an OS file lock. The log rotates at 1 MB.

## Tests and CI

`just test` runs the unit tests. They use fake adb and scrcpy processes, so no phone is needed.

CI (`.github/workflows/ci.yml`) runs them on Windows and Linux (Python 3.11 and 3.13) and on macOS (3.13), and checks that `uv tool install .` works.

## Releasing

```sh
just release 0.2.0
```

From a clean `main`, this:
1. updates `__version__` (the only place the version is defined)
2. runs the tests
3. commits, tags `v0.2.0` and pushes

The *Release* workflow (`.github/workflows/release.yml`) then:
1. checks that the tag matches the version
2. runs the tests
3. builds the wheel and source archive with `uv build`
4. publishes a GitHub Release with both files and the install command

## Icons

`icons.py` draws the app and tray icons from Lucide's `monitor-smartphone` icon (ISC, see `THIRD_PARTY_NOTICES.txt`). The images in `docs/images/` were generated with it.
