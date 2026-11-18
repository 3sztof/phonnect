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
- **Temporary phone settings** (`phone_state.py`): Force landscape (`cmd window user-rotation`) and content size (`wm density`). The phone's own value is saved to `rotation.json` / `density.json` before the first change and restored afterwards, including on the next connect if the phone was unreachable. One worker thread per setting, so changes and restores never race.
- **Sidebar** (`sidebar.py`, Tk): one process per mirror window. On Windows it docks to the scrcpy window: it's owned by that window, follows its DWM frame bounds every 30 ms, and uses `WS_EX_NOACTIVATE` so clicks don't steal the keyboard. Buttons write to a long-lived `adb shell`.
- **Control channel** (`control.py`): the tray is the only process that changes phone settings and `config.json`. Sidebars and `scrcpy-autolaunch mirror` reach it over 127.0.0.1 with a random token (passed to sidebars in their environment, and written to a user-only file for the CLI).
- **Themed scrcpy title bar:** the watcher finds the scrcpy window and sets `DWMWA_USE_IMMERSIVE_DARK_MODE` on it.
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

## Look and feel

`theme.py` makes the Tk windows match the OS, in light or dark mode:
- **Windows:** the [Sun Valley](https://github.com/rdbende/Sun-Valley-ttk-theme) theme (`sv-ttk`, MIT), which gives Windows 11 Fluent widgets. Title bars are switched to dark through the documented DWM attribute. Tray menus follow the system light/dark mode through uxtheme's `SetPreferredAppMode`. That call is undocumented but long-stable, and the app falls back to light menus if it's missing.
- **macOS:** Tk's own Aqua theme already follows the system, so nothing is needed.
- **Linux:** Tk's built-in `clam` theme, recoloured with GNOME's Adwaita palette. (`ttkthemes` was skipped because it's GPL-3.0.)

Light or dark is detected with `darkdetect`. The tray menu itself is always drawn by the OS.

## Icons

`icons.py` draws the app and tray icons from Lucide's `monitor-smartphone` icon (ISC, see `THIRD_PARTY_NOTICES.txt`). The images in `docs/images/` were generated with it.
