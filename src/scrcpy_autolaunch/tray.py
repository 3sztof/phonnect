"""System tray / menu bar icon around the watcher."""

from __future__ import annotations

import logging
import subprocess
import sys
import threading

from scrcpy_autolaunch import autostart, paths
from scrcpy_autolaunch.adb import WIRELESS, Adb
from scrcpy_autolaunch.config import Config
from scrcpy_autolaunch.osutil import IS_MAC, IS_WINDOWS, NO_WINDOW, gui_python, open_path
from scrcpy_autolaunch.watcher import Watcher
from scrcpy_autolaunch.wireless import KnownDevices, reconnect, status_of, wireless_serial_for

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


def icon_class(pystray):
    """On Windows, open the menu on left click too (pystray only does right click)."""
    if not IS_WINDOWS:
        return pystray.Icon  # macOS and most Linux trays already open the menu on left click
    from pystray import _win32

    class LeftClickMenuIcon(_win32.Icon):
        def _on_notify(self, wparam, lparam):
            if lparam == _win32.win32.WM_LBUTTONUP:
                lparam = _win32.win32.WM_RBUTTONUP
            super()._on_notify(wparam, lparam)

    return LeftClickMenuIcon


class TrayApp:
    def __init__(self, config: Config, adb: Adb | None, scrcpy: str | None, version, problem: str | None):
        import pystray

        self.pystray = pystray
        self.config = config
        self.adb = adb
        self.problem = problem
        self.known = KnownDevices()
        self._connecting: set[str] = set()
        self.watcher = (
            Watcher(config, adb, scrcpy, version, on_change=self.refresh, notify=self.notify, known=self.known)
            if adb and scrcpy
            else None
        )
        self.icon = icon_class(pystray)(
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
            "Hide phone keyboard while mirroring",
            self._toggle("hide_phone_keyboard"),
            checked=lambda _: self.config.hide_phone_keyboard,
        )
        yield Item(
            "Wi-Fi devices",
            Menu(self._wifi_items),
            enabled=self.adb is not None,
        )
        yield Menu.SEPARATOR
        yield Item("Start at login", self._toggle_autostart, checked=lambda _: autostart.is_enabled())
        yield Item("Open log", lambda *_: self._open(paths.log_file()))
        yield Item("Open settings folder", lambda *_: self._open(paths.config_dir()))
        yield Item("Quit", self.quit)

    def _wifi_items(self):
        Item, Menu = self.pystray.MenuItem, self.pystray.Menu
        devices = [d for d, _ in self.watcher.snapshot()] if self.watcher else []
        known = self.known.all()
        for k in known:
            if k.hw_id in self._connecting:
                text = f"{k.label}: connecting…"
            else:
                text = f"{k.label}: {status_of(k, devices)}"
            yield Item(text, self._wifi_toggle(k.hw_id), checked=self._wifi_checked(k.hw_id))
        if not known:
            yield Item("No paired phones yet", None, enabled=False)
        yield Menu.SEPARATOR
        yield Item("Manage Wi-Fi devices…", lambda *_: self._dialog("devices"))
        yield Item("Pair new device…", lambda *_: self._dialog("pair"))
        yield Item("Connect to address…", lambda *_: self._dialog("connect"))
        yield Item("Disconnect all Wi-Fi devices", lambda *_: self._background(self._disconnect))

    def _wifi_checked(self, hw_id: str):
        def checked(_item):
            k = self.known.get(hw_id)
            devices = [d for d, _ in self.watcher.snapshot()] if self.watcher else []
            return k is not None and status_of(k, devices) == "Wi-Fi"

        return checked

    def _wifi_toggle(self, hw_id: str):
        """Click a phone: connect if it isn't connected over Wi-Fi, disconnect if it is."""

        def action(*_):
            k = self.known.get(hw_id)
            if k is None or self.adb is None or hw_id in self._connecting:
                return
            serial = wireless_serial_for(k, self.adb.devices())
            if serial is not None and status_of(k, self.adb.devices()) == "Wi-Fi":
                log.info("Disconnecting %s (%s)", k.label, serial)
                self._background(lambda: (self.adb.disconnect(serial), self.refresh()))
                return

            def work():
                self._connecting.add(hw_id)
                self.refresh()
                try:
                    ok, result = reconnect(self.adb, k, progress=lambda m: log.info("%s", m))
                finally:
                    self._connecting.discard(hw_id)
                if ok:
                    self.known.remember(hw_id, address=result)
                    log.info("Connected to %s at %s", k.label, result)
                    self.notify(f"Connected to {k.label} over Wi-Fi.")
                else:
                    log.warning("Could not connect to %s:\n%s", k.label, result)
                    # Notifications are easy to miss; show the details in the window.
                    self._dialog("devices", f"Could not connect to {k.label}.\n{result}")
                self.refresh()

            self._background(work)

        return action

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

    def _dialog(self, kind: str, message: str = "") -> None:
        cmd = [gui_python(), "-m", "scrcpy_autolaunch", "_dialog", kind]
        if message:
            cmd += ["--message", message]

        def wait():
            try:
                code = subprocess.run(cmd, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL).returncode
            except OSError as exc:
                code = -1
                log.error("Could not open dialog: %s", exc)
            if code == 3:
                self.notify(
                    "Tk is not available for this Python. Use the command line instead: "
                    "scrcpy-autolaunch pair IP:PORT CODE / connect IP:PORT / wifi"
                )
            self.refresh()  # the window may have paired or connected a phone

        self._background(wait)

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
