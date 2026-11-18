"""System tray / menu bar icon around the watcher."""

from __future__ import annotations

import logging
import subprocess
import sys
import threading

from scrcpy_autolaunch import autostart, paths
from scrcpy_autolaunch.adb import WIRELESS, Adb
from scrcpy_autolaunch.config import Config
from scrcpy_autolaunch.osutil import IS_MAC, NO_WINDOW, gui_python, open_path
from scrcpy_autolaunch.watcher import Watcher

log = logging.getLogger(__name__)

GREEN = (61, 220, 132, 255)  # Android green: a device is connected
GREY = (150, 150, 150, 255)  # waiting for a device
RED = (220, 60, 60, 255)  # adb/scrcpy not found


def make_icon(color: tuple[int, int, int, int]):
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Phone outline with a screen and a home bar.
    d.rounded_rectangle((16, 4, 48, 60), radius=7, fill=color)
    d.rounded_rectangle((20, 10, 44, 50), radius=2, fill=(30, 30, 30, 255))
    d.rounded_rectangle((27, 53, 37, 56), radius=1, fill=(30, 30, 30, 255))
    return img


class TrayApp:
    def __init__(self, config: Config, adb: Adb | None, scrcpy: str | None, version, problem: str | None):
        import pystray

        self.pystray = pystray
        self.config = config
        self.adb = adb
        self.problem = problem
        self.watcher = (
            Watcher(config, adb, scrcpy, version, on_change=self.refresh, notify=self.notify)
            if adb and scrcpy
            else None
        )
        self.icon = pystray.Icon(
            "scrcpy-autolaunch",
            icon=make_icon(RED if problem else GREY),
            title="scrcpy-autolaunch",
            menu=pystray.Menu(self._menu_items),
        )

    # ── run / stop ───────────────────────────────────────────────────────────

    def run(self) -> None:
        def setup(icon):
            icon.visible = True
            if self.watcher:
                self.watcher.start()
            else:
                self.notify(self.problem or "adb/scrcpy not found")

        self.icon.run(setup=setup)
        if self.watcher:
            self.watcher.stop()

    def quit(self, *_):
        log.info("Quit from tray menu")
        if self.watcher:
            self.watcher.stop()
        self.icon.stop()

    # ── state shown in the tray ──────────────────────────────────────────────

    def refresh(self) -> None:
        try:
            if self.problem:
                color = RED
            else:
                color = GREEN if self.watcher and self.watcher.snapshot() else GREY
            self.icon.icon = make_icon(color)
            self.icon.title = self._tooltip()
            self.icon.update_menu()
        except Exception:
            log.exception("Tray refresh failed")

    def notify(self, message: str) -> None:
        log.info("Notification: %s", message)
        try:
            self.icon.notify(message, "scrcpy-autolaunch")
        except Exception:
            pass  # not every Linux tray backend supports notifications

    def _status_lines(self) -> list[str]:
        if self.problem:
            return [self.problem]
        devices = self.watcher.snapshot() if self.watcher else []
        if not devices:
            return ["No device connected"]
        lines = []
        for dev, mirroring in devices:
            state = "mirroring" if mirroring else (dev.state if not dev.online else "connected")
            lines.append(f"{dev.label}: {state}")
        return lines

    def _tooltip(self) -> str:
        # Windows limits tooltips to 127 characters.
        return ("scrcpy-autolaunch\n" + "\n".join(self._status_lines()))[:127]

    # ── menu ─────────────────────────────────────────────────────────────────

    def _menu_items(self):
        Item, Menu = self.pystray.MenuItem, self.pystray.Menu
        has_watcher = self.watcher is not None
        for line in self._status_lines():
            yield Item(line, None, enabled=False)
        yield Menu.SEPARATOR
        yield Item("Mirror now", self._mirror_now, default=True, enabled=has_watcher)
        yield Item("Auto-launch on USB", self._toggle("auto_usb"), checked=lambda _: self.config.auto_usb)
        yield Item(
            "Auto-launch on Wi-Fi", self._toggle("auto_wireless"), checked=lambda _: self.config.auto_wireless
        )
        yield Item(
            "Wireless",
            Menu(
                Item("Pair new device…", lambda *_: self._dialog("pair")),
                Item("Connect to address…", lambda *_: self._dialog("connect")),
                Item("Find devices on network", lambda *_: self._background(self._discover)),
                Item("Disconnect all Wi-Fi devices", lambda *_: self._background(self._disconnect)),
            ),
            enabled=self.adb is not None,
        )
        yield Menu.SEPARATOR
        yield Item("Start at login", self._toggle_autostart, checked=lambda _: autostart.is_enabled())
        yield Item("Open log", lambda *_: self._open(paths.log_file()))
        yield Item("Open settings folder", lambda *_: self._open(paths.config_dir()))
        yield Item("Quit", self.quit)

    # ── actions ──────────────────────────────────────────────────────────────

    def _mirror_now(self, *_):
        if self.watcher:
            self._background(self.watcher.mirror_now)

    def _toggle(self, key: str):
        def action(*_):
            setattr(self.config, key, not getattr(self.config, key))
            self.config.save()
            log.info("Setting %s = %s", key, getattr(self.config, key))
            self.icon.update_menu()

        return action

    def _toggle_autostart(self, *_):
        try:
            if autostart.is_enabled():
                autostart.disable()
                log.info("Start at login disabled")
            else:
                path = autostart.enable()
                log.info("Start at login enabled: %s", path)
        except Exception as exc:
            log.exception("Changing start-at-login failed")
            self.notify(f"Could not change start at login: {exc}")
        self.icon.update_menu()

    def _open(self, path):
        try:
            if not path.exists():
                # No log yet: open the folder instead.
                path = path.parent if path.suffix else path
                path.mkdir(parents=True, exist_ok=True)
            open_path(path)
        except Exception as exc:
            self.notify(f"Could not open {path}: {exc}")

    def _dialog(self, kind: str) -> None:
        cmd = [gui_python(), "-m", "scrcpy_autolaunch", "_dialog", kind]

        def wait():
            try:
                code = subprocess.run(cmd, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL).returncode
            except OSError as exc:
                code = -1
                log.error("Could not open dialog: %s", exc)
            if code == 3:
                self.notify(
                    "Tk is not available for this Python. Use the command line instead: "
                    f"scrcpy-autolaunch {kind} IP:PORT{' CODE' if kind == 'pair' else ''}"
                )

        self._background(wait)

    def _discover(self) -> None:
        assert self.adb is not None
        try:
            services = [s for s in self.adb.mdns_services() if "tls-connect" in s.service]
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.notify(f"Network search failed: {exc}")
            return
        if not services:
            self.notify("No phones found. Turn on Wireless debugging on the phone (and pair it first).")
            return
        for s in services:
            ok, out = self.adb.connect(s.address)
            log.info("Connect %s (%s): %s", s.address, s.name, out)
        self.notify(f"Found {len(services)} phone(s) on the network; see the log for details.")

    def _disconnect(self) -> None:
        assert self.adb is not None
        if self.watcher and not any(d.transport == WIRELESS for d, _ in self.watcher.snapshot()):
            self.notify("No Wi-Fi devices connected.")
            return
        log.info("Disconnect all: %s", self.adb.disconnect())

    @staticmethod
    def _background(fn) -> None:
        def wrapped():
            try:
                fn()
            except Exception:
                log.exception("Tray action failed")

        threading.Thread(target=wrapped, daemon=True).start()


def hide_dock_icon() -> None:
    """macOS: run as a menu-bar-only app (no Dock icon). Best effort."""
    if not IS_MAC:
        return
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory  # type: ignore

        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except Exception:
        log.debug("Could not hide the Dock icon", exc_info=True)


def run_tray(config: Config, adb: Adb | None, scrcpy: str | None, version, problem: str | None) -> None:
    hide_dock_icon()
    app = TrayApp(config, adb, scrcpy, version, problem)
    log.info("Tray started (Python %s)", sys.version.split()[0])
    app.run()
    log.info("Tray stopped")
