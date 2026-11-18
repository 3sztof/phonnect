# Usage

## Tray menu

On Windows, left- or right-click the icon. On macOS and most Linux desktops, click it.

```
Pixel 9 Pro: mirroring (USB)          >  Show window / Stop mirroring / Disconnect Wi-Fi
Mirror Galaxy S24 (Wi-Fi)                 connected but no window yet: one click
Connect and mirror Pixel 7 (Wi-Fi)        paired or seen before: connects, then mirrors
Pixel 6: allow USB debugging on the phone needs your attention
---
Audio                                 >  Off / PC and phone / PC only
Force landscape
Wi-Fi                                 >  Pair new phone… / Connect to address… / Manage Wi-Fi phones… / Disconnect all
Settings                              >  Auto-launch on USB / on Wi-Fi, Keep Wi-Fi connected, Hide phone keyboard, Start at login, Open log, Open settings folder
---
Quit
```

- **Clicking a phone means "show me this phone".** It connects over Wi-Fi if needed and opens the window, whatever the auto-launch settings are. Auto-launch only decides what happens without a click.
- A phone on both USB and Wi-Fi is one entry, mirrored over USB.
- **Show window** (Windows) brings a mirror window hidden behind others to the front.
- The icon is green when a phone is connected, grey while it waits, and red if scrcpy or adb wasn't found. Hover over it for a status summary.
- **Quit** stops watching for phones. Open mirror windows stay open.

## When the window opens by itself

| | |
|---|---|
| **Auto-launch on USB** (on by default) | Plugging in the phone opens the window |
| **Auto-launch on Wi-Fi** (off by default) | The phone connecting over Wi-Fi opens the window |

Closing the window doesn't reopen it. The phone has to disconnect and connect again first (unplug and replug), or you click it in the menu.

**Closing a Wi-Fi window also ends the Wi-Fi connection** (and so does **Stop mirroring**), so the phone isn't left connected in the background. To keep it connected instead, turn on **Settings → Keep Wi-Fi connected after closing the window**. Either way, a phone whose window you closed isn't reopened automatically over Wi-Fi until you click it or plug it in. That matters because adb can quietly reconnect paired phones by itself.

## Settings

### Audio

| | |
|---|---|
| **Off** (default) | Sound stays on the phone, including Bluetooth speakers, headphones or amps |
| **PC and phone** | Plays on the PC *and* keeps playing on the phone. Needs Android 13+ and scrcpy 2.6+, and some apps opt out of audio capture |
| **PC only** | Sound moves to the PC, and the phone goes silent |

Changing it reopens an open window to apply it.

### Force landscape

Rotates the phone to landscape while it's mirrored, including apps that ask for portrait, which may then look letterboxed or stretched. It applies to an open window right away.

Your rotation setting (auto-rotate, or locked to portrait) is saved first, and put back when the window closes, when you turn this off, or when you quit. If the phone is unplugged mid-session, it's put back the next time the phone connects.

To rotate just once without locking, press scrcpy's own **Alt+R** in the mirror window.

### Hide phone keyboard while mirroring

On by default. scrcpy acts as a physical keyboard, so Android hides the on-screen keyboard and you type on the PC. Nothing changes on the phone permanently: the on-screen keyboard comes back when the window closes.

If typing comes out in the wrong layout, set it once on the phone: *Settings → System → Keyboard → Physical keyboard*. With a mirror window open, **Alt+K** jumps there. Changing this setting reopens an open window.

### Inside the mirror window

Everything scrcpy offers works as usual:
- drag and drop an APK to install it, or any other file to copy it to the phone
- clipboard sync
- keyboard shortcuts, such as Alt+F for fullscreen and Alt+R to rotate

See [scrcpy's shortcuts](https://github.com/Genymobile/scrcpy/blob/master/doc/shortcuts.md).

## Commands

| Command | |
|---|---|
| `scrcpy-autolaunch install` / `uninstall [--purge]` | Enable or remove start at login and the app menu entry. `--purge` also deletes settings and logs |
| `start` / `stop` | Start or stop the tray app in the background |
| `status` | Running? Start at login? Where are the tools and files? |
| `doctor` | Check scrcpy, adb, tray support and connected phones, with hints |
| `log [-n 30]` | Show the end of the log |
| `devices` | List adb devices |
| `wifi` / `wifi --reconnect NAME\|ID\|all` | List paired and remembered phones, or reconnect to them |
| `pair [IP:PORT CODE]` / `connect [IP:PORT]` | Wi-Fi pairing and connecting. Without arguments, a window opens |
| `discover [--connect]` / `disconnect [IP:PORT]` | Show what mDNS sees, or disconnect Wi-Fi phones |
| `tray` / `run` | Run in the foreground, with the tray or console-only (logging to the terminal) |

From a clone, `just start`, `just stop`, `just status`, `just doctor` and `just log` do the same.

## Config file

Settings changed in the tray are saved immediately. You can also edit the file directly, then restart the app (`scrcpy-autolaunch stop`, then `start`):

```json
{
  "auto_usb": true,
  "auto_wireless": false,
  "hide_phone_keyboard": true,
  "force_landscape": false,
  "keep_wifi_connected": false,
  "audio": "off",
  "scrcpy_args": ["--stay-awake"],
  "wireless_extra_args": ["--max-size=1600", "--video-bit-rate=6M"],
  "poll_interval": 1.0,
  "adb_path": null,
  "scrcpy_path": null
}
```

| Key | |
|---|---|
| `audio` | `"off"`, `"both"` (PC and phone) or `"pc"` |
| `scrcpy_args` | Extra [scrcpy options](https://github.com/Genymobile/scrcpy#user-documentation) for every window. The app adds `-s <serial>`, and the audio, keyboard and Wi-Fi options, itself |
| `wireless_extra_args` | Added for Wi-Fi windows. A lower resolution and bitrate keep Wi-Fi mirroring smooth and leave room for Bluetooth |
| `poll_interval` | How often (in seconds) it checks for phones |
| `adb_path`, `scrcpy_path` | Set these if the tools aren't found automatically |

## File locations

| | Windows | macOS | Linux |
|---|---|---|---|
| Settings | `%LOCALAPPDATA%\scrcpy-autolaunch\config.json` | `~/Library/Application Support/scrcpy-autolaunch/config.json` | `~/.config/scrcpy-autolaunch/config.json` |
| Log, remembered phones, icons | same folder | same folder | `~/.local/state/scrcpy-autolaunch/` |
| Start at login | `shell:startup\scrcpy-autolaunch.lnk` | `~/Library/LaunchAgents/io.github.3sztof.scrcpy-autolaunch.plist` | `~/.config/autostart/scrcpy-autolaunch.desktop` |
| App menu entry | Start menu: `scrcpy-autolaunch.lnk` | none | `~/.local/share/applications/scrcpy-autolaunch.desktop` |
| App | `uv tool dir` | `uv tool dir` | `uv tool dir` |

The log is capped at about 2 MB.
