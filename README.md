<p align="center">
  <img src="docs/images/icon.png" width="96" alt="scrcpy-autolaunch icon">
</p>

<h1 align="center">scrcpy-autolaunch</h1>

<p align="center">
  A small tray app that opens your Android phone's screen on your computer as soon as the phone connects, over USB or Wi-Fi.<br>
  Built on <a href="https://github.com/Genymobile/scrcpy">scrcpy</a>.
</p>

## Support

If scrcpy-autolaunch saves you a few clicks every day, you can support its development:

<p>
  <a href="https://github.com/sponsors/3sztof"><img src="https://img.shields.io/badge/GitHub%20Sponsors-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white" alt="Sponsor on GitHub"></a>
  &nbsp;
  <a href="https://buymeacoffee.com/3sztof"><img src="https://img.shields.io/badge/Buy%20me%20a%20coffee-%E2%98%95-ffdd00?logo=buymeacoffee&logoColor=black" alt="Buy me a coffee"></a>
</p>

---

## The idea

[scrcpy](https://github.com/Genymobile/scrcpy) is great at mirroring and controlling an Android phone, but you have to start it every time. **scrcpy-autolaunch** sits in your tray (menu bar on macOS), watches for your phone and starts scrcpy for you:

- **Plug in the phone → the mirror window opens.** Close the window and it stays closed until you plug the phone in again.
- **Same over Wi-Fi:** pair once, then open the phone from the tray with one click, or let it open by itself.
- **Nothing else to manage:** no console window, it starts at login, and only one copy runs.

<p>
  <img src="docs/images/tray-waiting.png" width="24" alt=""> waiting for a phone &nbsp;
  <img src="docs/images/tray-connected.png" width="24" alt=""> phone connected &nbsp;
  <img src="docs/images/tray-problem.png" width="24" alt=""> scrcpy or adb not found
</p>

## The tray menu

```
Pixel 9 Pro: mirroring (USB)        >  Show window / Stop mirroring / Open shell / Disconnect Wi-Fi
Connect and mirror Pixel 7 (Wi-Fi)
---
Audio                               >  Off / PC and phone / PC only
Force landscape
Wi-Fi                               >  Pair new phone… / Connect to address… / Manage Wi-Fi phones…
Settings                            >  Auto-launch on USB / Wi-Fi, Hide phone keyboard, Start at login, Log
---
Quit
```

Your phones come first: **click a phone to see it.** The app connects over Wi-Fi if needed and opens the window. Everything else is optional:

| | |
|---|---|
| **Audio** | Off by default, so sound stays on the phone, including Bluetooth speakers or amps. You can also play it on the PC, alongside the phone or instead of it |
| **Force landscape** | Rotates the phone while it's mirrored, and puts it back afterwards |
| **Hide phone keyboard** | You type on the PC, and the phone's on-screen keyboard stays out of the way |
| **Sidebar** | A button bar glued to the mirror window: back, home, recent apps, notifications, volume, power, screenshot, an adb shell, and a slider to fit more on the screen |

More in [docs/usage.md](docs/usage.md).

## Install

You need **scrcpy + adb** and **[uv](https://docs.astral.sh/uv/)**:

| | scrcpy + adb |
|---|---|
| Windows | `winget install Genymobile.scrcpy` |
| macOS | `brew install scrcpy && brew install --cask android-platform-tools` |
| Linux | `sudo apt install scrcpy adb` (or your distro's equivalent) |

Then install the [latest release](https://github.com/3sztof/scrcpy-autolaunch/releases/latest) with the command shown on its page, which looks like this:

```sh
uv tool install --force --python ">=3.11" https://github.com/3sztof/scrcpy-autolaunch/releases/download/v0.2.0/scrcpy_autolaunch-0.2.0-py3-none-any.whl
scrcpy-autolaunch install
```

`install` enables start at login, adds a Start menu entry (an app launcher entry on Linux) and starts the tray app. For installing from a clone with `just`, upgrading and uninstalling, see [docs/installation.md](docs/installation.md).

## Set up the phone (once)

1. *Settings → About phone*: tap **Build number** 7 times to unlock Developer options.
2. *Settings → System → Developer options*: turn on **USB debugging**.
3. Plug the phone in and tap **Always allow from this computer**.

That's it: the mirror window opens. **New to this?** Follow the [step-by-step phone setup guide](docs/phone-setup.md). It covers other phone brands, what each prompt means, Wi-Fi, and how to turn it all off again.

## Platforms

| | |
|---|---|
| Windows 10/11 | Tested |
| macOS, Linux | Experimental: unit tests pass in CI, but nobody has tried it with a real phone yet |

## Documentation

- [Phone setup](docs/phone-setup.md): a step-by-step guide for first-timers, covering USB, Wi-Fi and how to turn it off again
- [Installation](docs/installation.md): requirements, release and clone installs, upgrading, uninstalling, migrating from the legacy version
- [Usage](docs/usage.md): tray menu, settings, commands, config file, file locations
- [Wi-Fi](docs/wifi.md): pairing, connecting, how reconnecting works
- [Troubleshooting](docs/troubleshooting.md): no window on plug-in, offline phones, black screens in secure apps, Linux and macOS notes
- [Development](docs/development.md): how it works, tests, releasing

The original PowerShell + VBS version (Windows only) is on the [`legacy-windows`](https://github.com/3sztof/scrcpy-autolaunch/tree/legacy-windows) branch.

## License

[MIT](LICENSE). The icon is based on [Lucide](https://lucide.dev)'s `monitor-smartphone` icon (ISC); see [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).
