# scrcpy-autolaunch

Automatically opens an [scrcpy](https://github.com/Genymobile/scrcpy) mirror window the moment you plug in your Android phone over USB — no manual commands, no console window. Closing the mirror window does **not** relaunch it; only unplugging and replugging the phone does.

Built for Windows. Mirrors the screen only: phone audio stays on the phone (`--no-audio`), and Bluetooth is never touched.

---

## Requirements

- Windows 10/11
- [scrcpy](https://github.com/Genymobile/scrcpy) + adb — install via winget:
  ```
  winget install Genymobile.scrcpy
  ```
- [just](https://github.com/casey/just) — task runner used for install/uninstall:
  ```
  winget install Casey.Just
  ```
  (or, if you have [uv](https://docs.astral.sh/uv/): `uv tool install rust-just`)
- USB debugging enabled on the phone (see [Phone setup](#phone-setup) below)

---

## Install

```
git clone https://github.com/3sztof/scrcpy-autolaunch
cd scrcpy-autolaunch
just install
just start
```

`just install` copies the files to `%USERPROFILE%\scrcpy-auto\` and drops a silent VBScript launcher into your Startup folder so the watcher runs automatically at every login.

`just start` starts the watcher immediately without requiring a logout.

> Clone the repo somewhere other than `%USERPROFILE%\scrcpy-auto` — that folder is the install target and `just uninstall` deletes it. The recipes refuse to run from there.

---

## Phone setup

Do this once before first use:

1. **Enable Developer Options** — *Settings → About phone*, tap **Build number** 7 times.
2. **Enable USB Debugging** — *Settings → Developer options → USB debugging*.
3. Plug the phone in via USB.
4. Tap **"Always allow from this computer"** on the authorization prompt.
5. Verify: `adb devices` should show your device as `device` (not `unauthorized`).

---

## Usage

| Command | What it does |
|---|---|
| `just install` | Copy files + register autostart entry |
| `just uninstall` | Stop watcher, remove autostart entry and all files |
| `just start` | Start the watcher now (no logout needed) |
| `just stop` | Kill the running watcher |
| `just status` | Show whether the watcher is running |
| `just log` | Print the last 20 lines of the event log |

---

## How it works

```
Login
  └─ shell:startup\scrcpy-auto-launch.vbs   (hidden, no console flash)
       └─ powershell -WindowStyle Hidden
            └─ scrcpy-auto.ps1  (named mutex → single instance)
                 ├─ adb wait-for-device        ← blocks until phone plugged in
                 ├─ scrcpy --no-audio --stay-awake --select-usb   ← mirror window appears
                 ├─ wait for scrcpy to exit
                 ├─ poll adb devices every 2 s until phone is unplugged
                 └─ loop
```

Events are logged to `%USERPROFILE%\scrcpy-auto\scrcpy-auto.log` with timestamps. The log is automatically trimmed when it exceeds 1 MB.

---

## Audio and Bluetooth

Since scrcpy 2.0, audio is forwarded to the PC by default on Android 11+, which means it stops playing on the phone. That would pull e.g. backing tracks away from a Bluetooth amp. This tool therefore launches scrcpy with `--no-audio --stay-awake --select-usb`: the phone keeps its own audio output, and Bluetooth connections (e.g. the Positive Grid Spark app to its amp) are left alone.

---

## Files

```
%USERPROFILE%\scrcpy-auto\
  scrcpy-auto.ps1          watcher script
  scrcpy-auto-launch.vbs   silent VBScript launcher (registered in Startup folder)
  scrcpy-auto.log          timestamped event log (auto-trimmed at 1 MB)
  README.md

Startup folder:
  %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
    scrcpy-auto-launch.vbs
```

---

## Uninstall

```
just uninstall
```

This stops the watcher, removes the Startup entry, and deletes `%USERPROFILE%\scrcpy-auto\`. scrcpy and adb themselves are unaffected.

To also remove scrcpy: `winget uninstall Genymobile.scrcpy`
