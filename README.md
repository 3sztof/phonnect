<p align="center">
  <img src="docs/images/icon.png" width="96" alt="Phonnect icon">
</p>

<h1 align="center">Phonnect</h1>

<p align="center">
  <b>Your Android phone on your desktop, as soon as you plug it in or come near (USB or Wi-Fi).</b><br>
  A small tray app that makes <a href="https://github.com/Genymobile/scrcpy">scrcpy</a> and adb effortless: it connects to your phone over USB or Wi-Fi and opens the mirror for you.<br>
  <sub>Formerly <i>scrcpy-autolaunch</i>.</sub>
</p>

## Support

If Phonnect saves you a few clicks every day, you can support its development:

<p>
  <a href="https://github.com/sponsors/3sztof"><img src="https://img.shields.io/badge/GitHub%20Sponsors-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white" alt="Sponsor on GitHub"></a>
  &nbsp;
  <a href="https://buymeacoffee.com/3sztof"><img src="https://img.shields.io/badge/Buy%20me%20a%20coffee-%E2%98%95-ffdd00?logo=buymeacoffee&logoColor=black" alt="Buy me a coffee"></a>
</p>

---

## The idea

Phonnect stands on the shoulders of two excellent tools:
- **[adb](https://developer.android.com/tools/adb)**, Android's own debugging bridge, which talks to the phone over USB or Wi-Fi, and
- **[scrcpy](https://github.com/Genymobile/scrcpy)**, which mirrors and controls the phone's screen with very low latency.

Both are powerful, but they're command-line tools: you start them by hand every time, and wireless use means pairing codes, IP addresses and ports that change. **Phonnect does that part for you.** It sits in your tray (menu bar on macOS), notices when your phone connects, and opens the mirror automatically:

- **Plug in the phone → the mirror window opens.** Close the window and it stays closed until you plug the phone in again.
- **Wi-Fi made easy:** pair once by scanning a QR code with the phone, and Phonnect remembers it. It finds it again after Android changes the debugging port (after a reboot or network change), so reconnecting is one click, or automatic.
- **Nothing else to manage:** no console window, it starts at login, and only one copy runs. scrcpy and adb stay the standard tools from your OS's package manager; Phonnect just drives them.

<p>
  <img src="docs/images/tray-waiting.png" width="24" alt=""> waiting for a phone &nbsp;
  <img src="docs/images/tray-connected.png" width="24" alt=""> phone connected &nbsp;
  <img src="docs/images/tray-problem.png" width="24" alt=""> scrcpy or adb not found
</p>

## Install

**macOS / Linux**, in a terminal:

```sh
curl -fsSL https://github.com/3sztof/phonnect/releases/latest/download/install.sh | sh
```

**Windows**, in PowerShell:

```powershell
irm https://github.com/3sztof/phonnect/releases/latest/download/install.ps1 | iex
```

The installer walks you through it. First it shows what it will install and where (the app, its commands, start at login, a Start menu / Spotlight / app launcher entry), and what's already there. Nothing happens until you say yes. It asks separately before installing [uv](https://docs.astral.sh/uv/) (which installs Phonnect and the Python it needs), and **scrcpy + adb** with your package manager (winget, Homebrew, apt, pacman, …). Everything goes into your user account, and nothing on your phone is changed.

**Updating:** when there's a new release, **Check for updates** in the tray menu becomes **Update Phonnect to X.Y.Z**. One click does it. Or run `phonnect update`.

**Uninstalling:** the same way, with `uninstall.sh` / `uninstall.ps1` in place of `install`. It asks whether to keep your settings, and leaves uv, scrcpy and adb in place.

Installing by hand, from a clone, and what goes where: [docs/installation.md](docs/installation.md).

## Set up the phone (once)

1. *Settings → About phone*: tap **Build number** 7 times to unlock Developer options.
2. *Settings → System → Developer options*: turn on **USB debugging**.
3. Plug the phone in and tap **Always allow from this computer**.

That's it: the mirror window opens. **New to this?** Follow the [step-by-step phone setup guide](docs/phone-setup.md). It covers other phone brands, what each prompt means, Wi-Fi, and how to turn it all off again.

## The tray menu

```
Pixel 9 Pro: mirroring (USB)  >  Show window · Stop mirroring · Open desktop mode · Open shell
Mirror Pixel 7 (Wi-Fi)
───────────
Audio                         >  Off · PC and phone · PC only
Force landscape
Wi-Fi                         >  Pair new phone (QR code or code)… · Connect to address… · Manage Wi-Fi phones… ·
                                 Disconnect all
Settings                      >  Auto-launch on USB / Wi-Fi · Keep Wi-Fi connected · Port scan · Show sidebar ·
                                 Hide phone keyboard · Mouse buttons · Start at login · Check for updates automatically ·
                                 Open log / settings
Check for updates                becomes "Update Phonnect to X.Y.Z" (one click) when there's a new release
───────────
Quit
```

Your phones come first: **click a phone to see it.** The app connects over Wi-Fi if needed and opens the window. Everything else is optional:

| | |
|---|---|
| **Audio** | Off by default, so sound stays on the phone, including Bluetooth speakers or amps. You can also play it on the PC, alongside the phone or instead of it |
| **Force landscape** | Rotates the phone while it's mirrored, and puts it back afterwards |
| **Hide phone keyboard** | You type on the PC, and the phone's on-screen keyboard stays out of the way |
| **Sidebar** | A button bar glued to the mirror window: back, home, recent apps, notifications, volume, power, screenshot, an adb shell, and a slider to fit more on the screen |
| **Desktop mode** | The phone's desktop (taskbar, app drawer, big-screen apps) in a second, PC-sized window, as if plugged into a monitor |

More in [docs/usage.md](docs/usage.md).

## Command line

Everything in the tray also works from a terminal, which is handy for scripts and troubleshooting:

```sh
phonnect status        # running? where are scrcpy, adb, settings and the log?
phonnect doctor        # check scrcpy, adb and your phone, with hints
phonnect mirror        # open the mirror window(s) now
phonnect pair --qr     # pair a Wi-Fi phone by scanning a QR code in the terminal
phonnect wifi          # list Wi-Fi phones; --reconnect all to connect them
phonnect update        # install a new release
phonnect log           # the end of the log
```

`phonnect --help` lists all commands; [docs/usage.md](docs/usage.md#commands) explains them.

## Platforms

| | |
|---|---|
| Windows 10/11 | Main platform: developed and tested here with real phones |
| macOS | Tested with a real phone, but not the main platform: likely less stable than on Windows |
| Linux | Untested: unit tests pass in CI, but nobody has tried it with a real phone yet |

## Documentation

- [Phone setup](docs/phone-setup.md): a step-by-step guide for first-timers, covering USB, Wi-Fi and how to turn it off again
- [Installation](docs/installation.md): requirements, release and clone installs, upgrading, uninstalling, migrating from the legacy version
- [Usage](docs/usage.md): tray menu, settings, commands, config file, file locations
- [Wi-Fi](docs/wifi.md): pairing, connecting, how reconnecting works
- [Troubleshooting](docs/troubleshooting.md): no window on plug-in, offline phones, black screens in secure apps, Linux and macOS notes
- [Development](docs/development.md): how it works, tests, releasing
- [Security](SECURITY.md): reporting a problem privately, what Phonnect does on your network

The original PowerShell + VBS version (Windows only) is on the [`legacy-windows`](https://github.com/3sztof/phonnect/tree/legacy-windows) branch.

## License

[MIT](LICENSE). The icon is based on [Lucide](https://lucide.dev)'s `monitor-smartphone` icon (ISC); see [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).
