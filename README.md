# scrcpy-autolaunch

Opens an [scrcpy](https://github.com/Genymobile/scrcpy) mirror window as soon as your Android phone connects over USB (and, optionally, Wi-Fi). It runs as a small tray icon (menu bar icon on macOS) with no console window.

- **USB:** plug the phone in and the mirror opens. Closing the window doesn't reopen it until you unplug and replug.
- **Wi-Fi (optional):** pair the phone once from the tray menu, then connect from the tray or let it auto-launch.
- **Audio stays on the phone:** scrcpy runs with `--no-audio`, so audio keeps playing on the phone, including over Bluetooth (for example, the Positive Grid Spark app's backing tracks to the amp). Bluetooth itself is never touched.
- **One instance only**, with a timestamped log that stays small (about 2 MB at most).

| Platform | Status |
|---|---|
| Windows 10/11 | Tested |
| macOS | Experimental: unit tests run in CI, not yet tested with a real phone |
| Linux | Experimental: unit tests run in CI, not yet tested with a real phone; the tray needs a desktop with tray support |

> Looking for the original PowerShell + VBS version (Windows only, no dependencies)? It's on the [`legacy-windows`](https://github.com/3sztof/scrcpy-autolaunch/tree/legacy-windows) branch.

---

## Requirements

- **scrcpy and adb** (scrcpy 2.0 or newer recommended)
  - Windows: `winget install Genymobile.scrcpy` (includes adb)
  - macOS: `brew install scrcpy && brew install --cask android-platform-tools`
  - Linux: `sudo apt install scrcpy adb` (or your distro's equivalent)
- **[uv](https://docs.astral.sh/uv/)**: `just install` offers to install it if it's missing.
- **[just](https://github.com/casey/just)** (optional, only for the `just` commands): `uv tool install rust-just`, `winget install Casey.Just` or `brew install just`.

## Install

```sh
git clone https://github.com/3sztof/scrcpy-autolaunch
cd scrcpy-autolaunch
just install
```

`just install`:
1. Checks for uv, and if it's missing, shows the official install command and asks before running it.
2. Installs the app and its dependencies (`pystray`, `Pillow`) with `uv tool install`, in an environment of their own.
3. Runs `scrcpy-autolaunch doctor` to check for scrcpy, adb, tray support and connected devices.
4. Enables start at login and starts the tray app.

**Without just or a clone:**

```sh
uv tool install git+https://github.com/3sztof/scrcpy-autolaunch
scrcpy-autolaunch install
```

## Phone setup (once)

1. **Developer options:** *Settings → About phone*, tap **Build number** 7 times.
2. **USB debugging:** *Settings → System → Developer options → USB debugging*, turn it on.
3. Plug in the phone and tap **Always allow from this computer** on the prompt.

### Wi-Fi (optional, Android 11+)

1. Turn on *Developer options → Wireless debugging*. The phone and computer must be on the same network.
2. In the tray menu, choose **Wireless → Pair new device…**. On the phone, tap **Pair device with pairing code** and type the IP:port and code it shows.
3. The phone usually connects by itself after pairing. If it doesn't, use **Wireless → Find devices on network** or **Connect to address…**.
4. To auto-launch over Wi-Fi as well, turn on **Auto-launch on Wi-Fi**.

Notes on Wi-Fi:
- Many phones share one radio between Bluetooth and 2.4 GHz Wi-Fi. If Bluetooth audio stutters while mirroring, use 5 GHz Wi-Fi or USB. Wi-Fi sessions use a lower resolution and bitrate by default (see `wireless_extra_args` below).
- Android turns Wireless debugging off after a reboot and on network changes, and the port changes each time. Pairing is kept.
- "Unplugging" over Wi-Fi means the phone drops off the network or you turn Wireless debugging off. After you close the window, use **Mirror now** to reopen it.

## Tray menu

| Item | What it does |
|---|---|
| *(status lines)* | Connected phones, and whether each is being mirrored |
| **Mirror now** | Opens a window for every connected phone that doesn't have one (also the default click action on Windows) |
| Auto-launch on USB / Wi-Fi | Turns auto-launch on or off for each connection type |
| Wireless → … | Pair, connect, find on network, disconnect |
| Start at login | Adds or removes the start-at-login entry |
| Open log / Open settings folder | |
| Quit | Stops the watcher. Open scrcpy windows stay open |

The icon is green when a phone is connected, grey while it waits for one, and red if scrcpy or adb wasn't found.

## Commands

| `just` | `scrcpy-autolaunch` | |
|---|---|---|
| `just install` | `install` | Install, enable start at login, start |
| `just uninstall` | `uninstall --purge` | Stop, remove start at login, settings and logs, and the uv tool |
| `just start` / `just stop` | `start` / `stop` | Start or stop the tray app in the background |
| `just status` | `status` | Running? Start at login? Tool and file paths |
| `just doctor` | `doctor` | Check scrcpy, adb, tray libraries and devices |
| `just log` | `log [-n 30]` | Show the end of the log |
| | `devices` | List adb devices |
| | `pair [IP:PORT CODE]` / `connect [IP:PORT]` | Wireless pairing and connecting (a dialog opens if you leave out the arguments) |
| | `discover [--connect]` / `disconnect [IP:PORT]` | Find phones with Wireless debugging on, or disconnect |
| | `run` | Watcher without a tray icon, logging to the console |

## Files

| | Windows | macOS | Linux |
|---|---|---|---|
| Settings | `%LOCALAPPDATA%\scrcpy-autolaunch\config.json` | `~/Library/Application Support/scrcpy-autolaunch/config.json` | `~/.config/scrcpy-autolaunch/config.json` |
| Log, lock | same folder | same folder | `~/.local/state/scrcpy-autolaunch/` |
| Start at login | `shell:startup\scrcpy-autolaunch.lnk` | `~/Library/LaunchAgents/io.github.3sztof.scrcpy-autolaunch.plist` | `~/.config/autostart/scrcpy-autolaunch.desktop` |
| App | `uv tool dir` | `uv tool dir` | `uv tool dir` |

### Settings (`config.json`)

```json
{
  "auto_usb": true,
  "auto_wireless": false,
  "scrcpy_args": ["--no-audio", "--stay-awake"],
  "wireless_extra_args": ["--max-size=1600", "--video-bit-rate=6M"],
  "poll_interval": 1.0,
  "adb_path": null,
  "scrcpy_path": null
}
```

`scrcpy_args` are passed to every session, and `wireless_extra_args` are added for Wi-Fi sessions. The app adds `-s <serial>` itself. Set `adb_path` or `scrcpy_path` if the tools aren't found automatically. Restart the app (`just stop`, then `just start`) after editing the file. Settings changed from the tray menu apply immediately.

## How it works

The watcher runs `adb devices -l` once a second. A phone that shows up, or becomes authorized, gets a scrcpy window if auto-launch is on for its connection type. A phone is only treated as "new" again after it disappears from adb, which is how closing the window avoids an instant relaunch. If the same phone is connected over both USB and Wi-Fi, it's recognized by its hardware serial number and gets one window, over USB. scrcpy is started with `ADB` set to the same adb binary, so two different adb versions don't keep restarting each other's server.

## Platform notes

**Linux**
- Tray: GNOME needs the *AppIndicator and KStatusNotifierItem Support* extension. KDE, XFCE and Cinnamon work out of the box.
- If `adb devices` shows `no permissions`, install your distro's udev rules (`android-udev` / `android-sdk-platform-tools-common`) or add a rule for your phone, then replug.
- The pairing dialog uses Tk: install `python3-tk` if the dialog doesn't open. You can also use `scrcpy-autolaunch pair IP:PORT CODE`.

**macOS**
- Start at login uses a LaunchAgent, which has Homebrew's paths added to its PATH.
- The first time scrcpy runs, macOS may ask for permissions.

## Migrating from legacy

If you installed the PowerShell version from `legacy-windows`, remove it first, or you'll get two windows:

1. Stop it: end the `powershell.exe` process whose command line contains `scrcpy-auto.ps1`.
2. Delete `shell:startup\scrcpy-auto-launch.vbs`.
3. Delete `%USERPROFILE%\scrcpy-auto\`.

`scrcpy-autolaunch doctor` warns you if the old Startup entry is still there.

## Uninstall

```sh
just uninstall
```

or, without just: `scrcpy-autolaunch uninstall --purge`, then `uv tool uninstall scrcpy-autolaunch`. scrcpy and adb are not touched.

## Development

```sh
just test      # unit tests
just dev-tray  # run the tray from the checkout
just dev-run   # run the console watcher from the checkout
```

## License

MIT
