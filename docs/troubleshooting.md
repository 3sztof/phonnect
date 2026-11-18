# Troubleshooting

Start with `scrcpy-autolaunch doctor`. It checks scrcpy, adb, tray support and connected phones, and explains what it finds. `scrcpy-autolaunch log` shows what the app saw.

## Plugging in the phone doesn't open a window

- **USB debugging is off.** The PC beeps, but only a file-transfer device appears, and `adb devices` doesn't list the phone. Turn on *Developer options → USB debugging*. If the phone is also connected over Wi-Fi, `doctor` and the log say this explicitly.
- **The phone isn't authorized.** The menu shows *allow USB debugging on the phone*. Unlock the phone and tap **Allow**, with **Always allow from this computer** ticked.
- **The phone is locked.** Android 16+ with Advanced Protection blocks USB data while the phone is locked. Unlock it.
- **The cable carries power only.** Some cables can't carry data. Try another cable or port.
- **Auto-launch on USB is off:** check *Settings* in the tray menu.
- **You closed the window.** It stays closed until you unplug and replug, or click the phone in the menu.

## The menu says "mirroring", but there's no window

On Windows, use the phone's **Show window** item to bring it to the front. If that doesn't help, choose **Stop mirroring** and click the phone again.

## A Wi-Fi phone shows as offline, or won't connect

See [wifi.md](wifi.md#why-connecting-can-fail-and-how-reconnecting-works). In short:
- Wireless debugging has to be on.
- The port changes, and the app finds the new one.
- Connect to the address on the *Wireless debugging* screen, not the pairing port.

## Some apps show a black screen

Banking, password, payment and DRM video apps mark their windows as *secure* (Android's `FLAG_SECURE`). Android then leaves them out of every screenshot, screen recording and screen share, scrcpy included. That's an Android security rule, and nothing on the PC side can get around it.

The only workarounds need a rooted phone and a module that removes the flag. That weakens the phone's security, often makes those same apps refuse to run, and may break their terms of use, so this project doesn't do it.

Separately, Android 15+ can hide notification contents and one-time codes during screen sharing. If you see that, *Developer options → Disable screen share protections* turns it off. It doesn't affect secure apps.

## Two mirror windows open

Another tool is mirroring too, for example QtScrcpy, or the legacy PowerShell watcher (see [installation.md](installation.md#migrating-from-the-legacy-version)). Run only one, or turn off **Auto-launch on USB** while you use the other.

If tools with different adb versions keep disconnecting the phone, point them at the same adb (`adb_path` in [usage.md](usage.md#config-file)).

## Linux

- **No tray icon:** GNOME needs the *AppIndicator and KStatusNotifierItem Support* extension. KDE, XFCE and Cinnamon work out of the box.
- **`no permissions` in `adb devices`:** install your distro's Android udev rules (`android-udev`, `android-sdk-platform-tools-common`, or similar), then replug.
- **The pairing window doesn't open:** install `python3-tk`, or use `scrcpy-autolaunch pair IP:PORT CODE`.

## macOS

- Start at login uses a LaunchAgent, which has Homebrew's paths added to its PATH.
- The first time scrcpy runs, macOS may ask for permissions.
