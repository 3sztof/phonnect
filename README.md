# scrcpy-autolaunch

Opens an [scrcpy](https://github.com/Genymobile/scrcpy) mirror window as soon as your Android phone connects over USB (and, optionally, Wi-Fi). It runs as a small tray icon (menu bar icon on macOS) with no console window.

- **USB:** plug the phone in and the mirror opens. Closing the window doesn't reopen it until you unplug and replug.
- **Wi-Fi (optional):** pair the phone once from the tray menu, then connect from the tray or let it auto-launch.
- **Audio stays on the phone by default**, including over Bluetooth (for example, the Positive Grid Spark app's backing tracks to the amp). The **Audio** menu can also play sound on the PC, either alongside the phone or instead of it. Bluetooth itself is never touched.
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
- **[uv](https://docs.astral.sh/uv/)**: `just install` offers to install it if it's missing. Python 3.11 or newer is needed, and uv downloads it if your system doesn't have it.
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
4. Enables start at login, adds an app menu entry (Start menu on Windows, app launcher on Linux) and starts the tray app.

**Without just or a clone:**

```sh
uv tool install --python ">=3.11" git+https://github.com/3sztof/scrcpy-autolaunch
scrcpy-autolaunch install
```

## Starting and stopping

It starts by itself at login. To start it by hand, use any of:
- **Windows:** the **scrcpy-autolaunch** entry in the Start menu
- **Linux:** the app launcher
- **Any OS:** `scrcpy-autolaunch start` (or `just start`)

Only one copy runs, so starting it again does nothing. Quit from the tray menu, or run `scrcpy-autolaunch stop`.

It isn't listed under Windows "Installed apps", because uv manages it. To remove it, use `just uninstall` (see [Uninstall](#uninstall)).

## Phone setup (once)

1. **Developer options:** *Settings → About phone*, tap **Build number** 7 times.
2. **USB debugging:** *Settings → System → Developer options → USB debugging*, turn it on.
3. Plug in the phone and tap **Always allow from this computer** on the prompt.

### Wi-Fi (optional, Android 11+)

1. Turn on *Developer options → Wireless debugging*. The phone and computer must be on the same network.
2. In the tray menu, choose **Wi-Fi → Pair new phone…**. On the phone, tap **Pair device with pairing code** and type the IP:port and code it shows. The app connects right after pairing.
3. After that, the phone appears at the top of the tray menu. Click **Connect and mirror …** to connect over Wi-Fi and open the window. **Wi-Fi → Manage Wi-Fi phones…** opens a window with every paired phone, its status and any error details.
4. To have it open the window by itself whenever the phone connects over Wi-Fi, turn on **Settings → Auto-launch on Wi-Fi**.

**Why connecting can fail, and how reconnecting works:** Android picks a **new port** every time Wireless debugging turns on, after a reboot or a network change. The **IP address** usually stays the same, depending on your router's DHCP. To make it permanent, give the phone a DHCP reservation. The app remembers each phone's IP, learned over USB or Wi-Fi, and reconnects in this order:
1. **mDNS:** the phone advertises its current port. This is fast, but some networks and VPN adapters block it.
2. **The last address that worked.**
3. **A port scan** of the phone's last known IP for the new port. This takes about 10–15 s.

A phone shown as `offline` usually means `adb connect` used the wrong port, for example the one from the pairing popup. Stale `offline` entries are cleaned up before each connect attempt.

Notes on Wi-Fi:
- Many phones share one radio between Bluetooth and 2.4 GHz Wi-Fi. If Bluetooth audio stutters while mirroring, use 5 GHz Wi-Fi or USB. Wi-Fi sessions use a lower resolution and bitrate by default (see `wireless_extra_args` below).
- "Unplugging" over Wi-Fi means the phone drops off the network or you turn Wireless debugging off. After you close the window, use **Mirror now** to reopen it.

## Tray menu

On Windows, left- or right-click the icon to open the menu. Phones come first, because that's what you click most:

```
Pixel 9 Pro: mirroring (USB)          >  Show window / Stop mirroring / Disconnect Wi-Fi
Mirror Galaxy S24 (Wi-Fi)                 connected but no window yet: one click
Connect and mirror Pixel 7 (Wi-Fi)        paired or seen before: connects, then mirrors
---
Audio                                 >  Off / PC and phone / PC only
Wi-Fi                                 >  Pair new phone… / Connect to address… / Manage Wi-Fi phones… / Disconnect all
Settings                              >  Auto-launch on USB / on Wi-Fi, Hide phone keyboard, Start at login, Open log, Open settings folder
---
Quit
```

- **Clicking a phone means "show me this phone".** It connects over Wi-Fi if needed and opens the mirror, whatever the auto-launch settings are. Auto-launch only controls what happens *without* a click.
- A phone on both USB and Wi-Fi is one entry, mirrored over USB.
- A phone that needs attention (for example `allow USB debugging on the phone`) shows that as its entry.
- The icon is green when a phone is connected, grey while it waits for one, and red if scrcpy or adb wasn't found. Hovering over the icon shows a status summary.

| Setting | |
|---|---|
| Audio: **Off** (default) | Sound stays on the phone |
| Audio: **PC and phone** | Also plays on the PC while the phone keeps playing, for example to a Bluetooth amp (Android 13+, scrcpy 2.6+; apps can opt out of capture) |
| Audio: **PC only** | Sound moves to the PC, and the phone goes silent |
| Hide phone keyboard while mirroring | scrcpy acts as a physical keyboard (`--keyboard=uhid`), so the phone hides its on-screen keyboard and you type on the PC |

Changing the audio or keyboard setting reopens an open mirror window to apply it.

**About the keyboard option:** Android hides the on-screen keyboard whenever a physical keyboard is attached, and that's what scrcpy pretends to be. Nothing changes on the phone permanently, and the on-screen keyboard comes back when the window closes. If PC typing comes out in the wrong layout, set it once on the phone: *Settings → System → Keyboard → Physical keyboard* (with a window open, press Alt+K to get there). Turn the option off if you'd rather type on the phone itself.

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
| | `wifi` / `wifi --reconnect NAME\|ID\|all` | List paired and remembered phones, or reconnect (mDNS, then last address, then port scan) |
| | `pair [IP:PORT CODE]` / `connect [IP:PORT]` | Wireless pairing and connecting (a window opens if you leave out the arguments) |
| | `discover [--connect]` / `disconnect [IP:PORT]` | Show what mDNS sees, or disconnect |
| | `run` | Watcher without a tray icon, logging to the console |

## Files

| | Windows | macOS | Linux |
|---|---|---|---|
| Settings | `%LOCALAPPDATA%\scrcpy-autolaunch\config.json` | `~/Library/Application Support/scrcpy-autolaunch/config.json` | `~/.config/scrcpy-autolaunch/config.json` |
| Log, lock, remembered Wi-Fi phones | same folder | same folder | `~/.local/state/scrcpy-autolaunch/` |
| Start at login | `shell:startup\scrcpy-autolaunch.lnk` | `~/Library/LaunchAgents/io.github.3sztof.scrcpy-autolaunch.plist` | `~/.config/autostart/scrcpy-autolaunch.desktop` |
| App menu entry | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\scrcpy-autolaunch.lnk` | none | `~/.local/share/applications/scrcpy-autolaunch.desktop` |
| App | `uv tool dir` | `uv tool dir` | `uv tool dir` |

### Settings (`config.json`)

```json
{
  "auto_usb": true,
  "auto_wireless": false,
  "hide_phone_keyboard": true,
  "audio": "off",
  "scrcpy_args": ["--stay-awake"],
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
