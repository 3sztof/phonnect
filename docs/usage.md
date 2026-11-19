# Usage

## Tray menu

On Windows, left- or right-click the icon. On macOS and most Linux desktops, click it.

```
Pixel 9 Pro: mirroring (USB)          >  Show window / Stop mirroring / Open desktop mode / Open shell / Disconnect Wi-Fi
Mirror Galaxy S24 (Wi-Fi)                 connected but no window yet: one click
Connect and mirror Pixel 7 (Wi-Fi)        paired or seen before: connects, then mirrors
Pixel 6: allow USB debugging on the phone needs your attention
---
Audio                                 >  Off / PC and phone / PC only
Force landscape
Wi-Fi                                 >  Pair new phone… (QR code or pairing code) / Connect to address… /
                                         Manage Wi-Fi phones… / Disconnect all
Settings                              >  Auto-launch on USB
                                         Auto-launch on Wi-Fi
                                         Keep Wi-Fi connected after closing the window
                                         Find a Wi-Fi phone's new port by scanning it
                                         Show sidebar next to the window
                                         Reopen windows where they were (Windows)
                                         Hide phone keyboard while mirroring
                                         Mouse buttons >  Right click / Middle click / Side buttons
                                         Start at login
                                         Check for updates automatically
                                         Open log / Open settings folder
                                         Phonnect X.Y.Z (the installed version)
Check for updates                         becomes "Update Phonnect to X.Y.Z" when there's a new release
---
Quit
```

- **Clicking a phone means "show me this phone".** It connects over Wi-Fi if needed and opens the window, whatever the auto-launch settings are. Auto-launch only decides what happens without a click.
- A phone on both USB and Wi-Fi is one entry, mirrored over USB.
- **Show window** (Windows) brings a mirror window hidden behind others to the front.
- **Open shell** opens `adb shell` for that phone in your terminal app (on Windows, your default terminal, e.g. Windows Terminal).
- The icon is green when a phone is connected, and red if scrcpy or adb wasn't found. While it waits, it's white or black to match the other icons next to it (it follows dark and light mode). Hover over it for a status summary.
- **Updates live in one entry.** **Check for updates** asks GitHub now and tells you the result, including whether a newer scrcpy exists and how to update it (scrcpy and adb belong to your package manager, so Phonnect doesn't update them). When a new Phonnect release is out, the entry becomes **Update Phonnect to X.Y.Z**: one click updates it in a small terminal window, which closes by itself when it's done. The app stops first, putting phone settings back, and the new version starts. Settings and remembered phones are kept. With *Check for updates automatically* on (the default), it checks once a day by itself. It only asks GitHub's API for the latest release and sends nothing else.
- **Quit** stops watching for phones. Open mirror windows stay open, but the sidebars close and every phone setting the app changed (rotation, content size) is put back.

## The sidebar

A slim button bar next to each mirror window (on by default; **Settings → Show sidebar next to the window**):

| Button | |
|---|---|
| Back, Home, Recent apps | The phone's navigation buttons |
| Notifications, Quick settings | Pull down the notification shade or the quick-settings panel |
| Volume up / down, Power | The phone's side buttons. Power turns the phone screen off and on; the mirror keeps working |
| Screenshot | Saves a PNG to `Pictures\phonnect`. Right-click it to open that folder |
| Force landscape | Same as the tray setting (see below) |
| Desktop mode | Opens the phone's desktop in a second window (see below) |
| Shell | Opens `adb shell` for the phone in your terminal app |
| Content size slider | Drag down to fit more on the screen (see below) |

Hover over a button for its name. On **Windows and macOS** the bar is glued to the window's right edge (or left edge, if there's no room on the right): it follows when you move, resize or minimize the window, and clicking it doesn't take the keyboard away from the mirror (Windows). On macOS it stays above the mirror window while that's in front, and hides when the mirror goes full screen. On **Linux** it's a small floating window instead, because apps can't follow other windows reliably there.

Buttons go to the phone through one `adb shell` that stays open, so presses are instant. scrcpy's own shortcuts work as well (Alt+B back, Alt+H home, Alt+S recent apps, Alt+N notifications, Alt+P power).

The mirror window's title bar follows Windows' light/dark mode, like the rest of the app.

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

### Desktop mode

Opens Android's desktop experience in its own window, like plugging the phone into a monitor: a taskbar, an app drawer, and apps in big-screen layouts. It runs on a second screen, so the mirror window keeps showing the phone's own screen. Close the window to end it. **It's experimental.**

**Known problem on current Pixels (Android 16 and 17):** the desktop and its taskbar show, but clicking an app in the taskbar or app drawer does nothing. It's a problem between Android and scrcpy's virtual screens ([scrcpy #6699](https://github.com/Genymobile/scrcpy/issues/6699), [#7048](https://github.com/Genymobile/scrcpy/issues/7048)); a fix for scrcpy is proposed ([#7055](https://github.com/Genymobile/scrcpy/pull/7055)). Progress is tracked in [Phonnect issue #1](https://github.com/3sztof/phonnect/issues/1).

**The workaround: the Apps panel.** Until that's fixed, Phonnect docks an **Apps panel** next to the desktop window:

- search the phone's apps and double-click one (or press Enter) to open it on the desktop, full screen, or tick *Open in a window*;
- *Open on the desktop* lists what's running there: **Switch to** brings an app back to the front, **Close** closes it, **Desktop** shows the desktop again.

Apps opened this way have no title bars (the desktop's window management needs the same fix), so they can't be moved or resized; full screen plus *Switch to* works best. Nothing on the phone is changed.

**It asks first.** Because it's a workaround, desktop mode explains all this in a prompt before it opens. Tick *Don't show this again* to skip it next time.

**Experimental workaround, not recommended:** `"desktop_method": "overlay"` in the config file uses Android's *simulated second screen* (*Developer options → Simulate secondary displays*) instead, where apps do open. But on a Pixel 9 Pro (Android 17) it froze after about 20 seconds and Android restarted itself, and while it's on the phone shows a semi-transparent preview of the desktop that can't be hidden and may block PIN entry. Phonnect removes the simulated screen when the desktop window closes, on quit, or when the phone reconnects. **If the preview stays on the phone** (for example because the phone froze and dropped off): *Developer options → Simulate secondary displays → None* removes it. If the phone doesn't respond, restart it; the preview can take a little while to disappear after the restart.

- Needs scrcpy 3.0+, and on Pixels *Developer options → Enable desktop experience features* (then restart the phone). Without it you get the phone's launcher on the second screen instead of a desktop.
- Size and density come from `desktop_display` in the config file (default `1920x1080/160`; a higher number means larger text and icons, e.g. `1920x1080/240`).
- Sound stays with the main mirror window (the desktop window opens without audio). Content with copy protection (some video apps) may show black there.

### Content size

The sidebar's slider makes everything on the phone smaller, so more fits on the screen and the mirror looks less "zoomed in" on a big monitor. 100% is your phone's own display-size setting; at 50%, twice as much fits. It's applied when you let go of the slider.

Technically it's the phone's display density (`wm density`). Text and buttons get smaller **on the phone too** while you mirror, and apps briefly redraw when it changes. Your own setting is put back when the window closes, the phone disconnects, or you quit the app. If the phone was unplugged mid-session, it's put back as soon as it connects again. The last value you chose is remembered for the next window (`content_scale` in the config file).

### Mouse buttons

**Settings → Mouse buttons** sets what each extra mouse button does in the mirror window:

| Button | Default |
|---|---|
| Right click | Sent to the app, like a right click on a PC (most apps ignore it, some open a menu) |
| Middle click | Home |
| Side button (back) | Back, like in a browser |
| Side button (forward) | Recent apps |

Each can be set to: click in the app, Back, Home, Recent apps, Notifications, or nothing. Holding **Shift** while clicking always gives scrcpy's original shortcuts (right: Back, middle: Home, side buttons: Recent apps / Notifications). Changing it reopens an open window. **Escape** works as Back too, because Android treats it that way. Needs scrcpy 2.5 or newer.

### Hide phone keyboard while mirroring

On by default. scrcpy acts as a physical keyboard, so Android hides the on-screen keyboard and you type on the PC. Nothing changes on the phone permanently: the on-screen keyboard comes back when the window closes.

If typing comes out in the wrong layout, set it once on the phone: *Settings → System → Keyboard → Physical keyboard*. With a mirror window open, **Alt+K** jumps there. Changing this setting reopens an open window.

### Window size and position

On Windows, each phone's window opens where you left it last time, at the same height, for portrait and landscape separately (desktop mode has its own). The width always follows the phone's picture, so there are no black bars at the sides. If a window opens with bars anyway (scrcpy's first guess on wide screens), Phonnect trims them as soon as the picture arrives. If the remembered spot is on a monitor that's no longer there, the window opens at scrcpy's default position, keeping its size. Turn it off with **Settings → Reopen windows where they were**. On macOS and Linux, scrcpy picks the size and position.

### Inside the mirror window

Everything scrcpy offers works as usual:
- drag and drop an APK to install it, or any other file to copy it to the phone
- clipboard sync
- keyboard shortcuts, such as Alt+F for fullscreen and Alt+R to rotate

See [scrcpy's shortcuts](https://github.com/Genymobile/scrcpy/blob/master/doc/shortcuts.md).

## Commands

| Command | |
|---|---|
| `phonnect install` / `uninstall [--purge]` | Enable or remove start at login and the app menu entry. `--purge` also deletes settings and logs |
| `start` / `stop` | Start or stop the tray app in the background |
| `status` | Running? Start at login? Where are the tools and files? |
| `doctor` | Check scrcpy, adb, tray support and connected phones, with hints |
| `log [-n 30]` | Show the end of the log |
| `devices` | List adb devices |
| `mirror [PHONE]` | Ask the running app to open a mirror window (a phone name, serial, or all) |
| `wifi` / `wifi --reconnect NAME\|ID\|all` | List paired and remembered phones, or reconnect to them |
| `pair [IP:PORT CODE]` / `pair --qr` / `connect [IP:PORT]` | Wi-Fi pairing and connecting. `--qr` shows a QR code in the terminal to scan with the phone. Without arguments, a window opens |
| `discover [--connect]` / `disconnect [IP:PORT]` | Show what mDNS sees, or disconnect Wi-Fi phones |
| `update [--check]` | Check for a new release and install it (on Windows, in a new window) |
| `tray` / `run` | Run in the foreground, with the tray or console-only (logging to the terminal) |

From a clone, `just start`, `just stop`, `just status`, `just doctor` and `just log` do the same.

## Config file

Settings changed in the tray are saved immediately. You can also edit the file directly, then restart the app (`phonnect stop`, then `start`):

```json
{
  "auto_usb": true,
  "auto_wireless": false,
  "hide_phone_keyboard": true,
  "force_landscape": false,
  "keep_wifi_connected": false,
  "content_scale": 100,
  "show_sidebar": true,
  "remember_window": true,
  "check_updates": true,
  "wifi_port_scan": true,
  "desktop_display": "1920x1080/160",
  "desktop_method": "virtual",
  "desktop_confirmed": false,
  "mouse_buttons": {"right": "app", "middle": "home", "back": "back", "forward": "recents"},
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
