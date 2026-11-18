# Wi-Fi

Needs Android 11 or newer. The phone and the computer must be on the same network.

## Pair a phone (once)

1. On the phone: *Settings → System → Developer options → Wireless debugging*, turn it on.
2. In the tray: **Wi-Fi → Pair new phone…**
3. On the phone, tap **Pair device with pairing code**. Type the IP address & port and the 6-digit code it shows into the window on the PC.

The app connects right after pairing. From then on, the phone appears at the top of the tray menu.

## Connect

- **Click the phone in the tray menu** (*Connect and mirror …*). It connects and opens the window.
- To have the window open by itself whenever the phone connects over Wi-Fi, turn on **Settings → Auto-launch on Wi-Fi**.
- **Wi-Fi → Manage Wi-Fi phones…** opens a window listing every paired phone with its status, plus Connect, Disconnect and Pair buttons. Errors are shown there in full.
- If the app can't find the phone, use **Wi-Fi → Connect to address…** with the IP address & port shown on the phone's *Wireless debugging* screen. Don't use the port from the pairing popup.

From a terminal: `scrcpy-autolaunch wifi`, `wifi --reconnect all`, `pair`, `connect IP:PORT`.

## Why connecting can fail, and how reconnecting works

Android picks a **new port** every time Wireless debugging turns on: after a reboot, a network change or toggling it. The **IP address** usually stays the same, and a DHCP reservation on your router makes it permanent.

The app remembers each phone's IP, learned over USB or Wi-Fi, and tries in order:

1. **mDNS:** the phone advertises its current port. This is fast, but some networks and VPN adapters (such as Tailscale) block it.
2. **The last address that worked.**
3. **A scan** of the phone's IP for the new port. This takes about 10–15 seconds.

Before each attempt, stale `offline` entries are cleared. An `offline` phone usually means a connection was made to the wrong port, for example the pairing port.

## Things to know

- **Bluetooth and 2.4 GHz Wi-Fi often share one radio.** If Bluetooth audio stutters while mirroring over Wi-Fi, use 5 GHz Wi-Fi or USB. Wi-Fi windows use a lower resolution and bitrate by default (`wireless_extra_args` in [usage.md](usage.md#config-file)).
- **Wi-Fi has no "unplug".** The phone counts as disconnected when it leaves the network or Wireless debugging turns off. After closing the window, click the phone in the menu to reopen it.
- **Mirroring over Wi-Fi drains the battery faster,** because the screen stays on and the phone isn't charging.
