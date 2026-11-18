"""System tray / menu bar icon around the watcher.

Menu layout (phones first, because that's what you click most):

    Pixel 9 Pro - mirroring (USB)      >  Show window / Stop mirroring / Disconnect Wi-Fi
    Mirror Galaxy S24 (Wi-Fi)             (connected, not mirrored: one click)
    Connect and mirror Pixel 7 (Wi-Fi)    (known, not connected: one click)
    ---
    Audio                              >  Off / PC and phone / PC only
    Force landscape                       (checkbox)
    Wi-Fi                              >  Pair new phone / Connect to address / Manage / Disconnect all
    Settings                           >  auto-launch, keyboard, start at login, log, folder
    ---
    Quit
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field

from scrcpy_autolaunch import autostart, icons, paths, theme
from scrcpy_autolaunch.adb import USB, WIRELESS, Adb
from scrcpy_autolaunch.config import Config
from scrcpy_autolaunch.osutil import IS_MAC, IS_WINDOWS, NO_WINDOW, focus_process_window, gui_python, open_path
from scrcpy_autolaunch.watcher import Watcher
from scrcpy_autolaunch.wireless import KnownDevices, reconnect

log = logging.getLogger(__name__)

AUDIO_MODES = (
    ("off", "Off (sound stays on the phone)"),
    ("both", "PC and phone (Android 13+)"),
    ("pc", "PC only (phone goes silent)"),
)

STATE_TEXT = {
    "unauthorized": "allow USB debugging on the phone",
    "no permissions": "no USB permission (see README)",
    "offline": "not responding, replug it",
}


@dataclass
class PhoneRow:
    hw_id: str
    name: str
    # "mirroring" | "connected" | "connecting" | "available" | an adb state like "unauthorized"
    state: str
    via: list[str] = field(default_factory=list)  # "USB", "Wi-Fi"
    wifi_serial: str | None = None

    @property
    def via_text(self) -> str:
        return " + ".join(self.via)


def build_rows(phones, known, connecting: set[str]) -> list[PhoneRow]:
    """Merge connected phones (from the watcher) with remembered/paired ones."""
    rows: dict[str, PhoneRow] = {}
    for hw, devs, mirroring in phones:
        online = [d for d in devs if d.online]
        model = next((d.model for d in devs if d.model), "")
        name = model.replace("_", " ") or devs[0].serial
        if online:
            state = "mirroring" if mirroring else "connected"
        else:
            state = devs[0].state
        rows[hw] = PhoneRow(
            hw_id=hw,
            name=name,
            state=state,
            via=[("USB" if d.transport == USB else "Wi-Fi") for d in online],
            wifi_serial=next((d.serial for d in online if d.transport == WIRELESS), None),
        )
    for k in known:
        if k.hw_id in rows:
            if rows[k.hw_id].name == k.hw_id and k.model:
                rows[k.hw_id].name = k.label
            continue
        rows[k.hw_id] = PhoneRow(k.hw_id, k.label, "connecting" if k.hw_id in connecting else "available")
    order = {"mirroring": 0, "connected": 1, "connecting": 3, "available": 4}
    return sorted(rows.values(), key=lambda r: (order.get(r.state, 2), r.name))


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
        self._icon_state = "problem" if problem else "waiting"
        self.watcher = (
            Watcher(config, adb, scrcpy, version, on_change=self.refresh, notify=self.notify, known=self.known)
            if adb and scrcpy
            else None
        )
        if self.watcher is not None:
            from scrcpy_autolaunch.cli import attach_helpers

            attach_helpers(self.watcher)
            self.watcher.on_quit = self.quit
        self.icon = icon_class(pystray)(
            "scrcpy-autolaunch",
            icon=icons.tray_icon("problem" if problem else "waiting"),
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
            self.watcher.restore_all_phone_settings()
        from scrcpy_autolaunch.control import remove_endpoint

        remove_endpoint()
        self.icon.stop()

    # ── state shown in the tray ──────────────────────────────────────────────

    def rows(self) -> list[PhoneRow]:
        phones = self.watcher.phones() if self.watcher else []
        return build_rows(phones, self.known.all(), self._connecting)

    def refresh(self) -> None:
        try:
            rows = self.rows()
            if self.problem:
                state = "problem"
            else:
                state = "connected" if any(r.via for r in rows) else "waiting"
            if state != self._icon_state:
                self._icon_state = state
                self.icon.icon = icons.tray_icon(state)
            self.icon.title = self._tooltip(rows)
            self.icon.update_menu()
        except Exception:
            log.exception("Tray refresh failed")

    def notify(self, message: str) -> None:
        log.info("Notification: %s", message)
        try:
            self.icon.notify(message, "scrcpy-autolaunch")
        except Exception:
            pass  # not every Linux tray backend supports notifications

    def _tooltip(self, rows: list[PhoneRow]) -> str:
        if self.problem:
            lines = [self.problem]
        else:
            lines = [
                f"{r.name}: {r.state} ({r.via_text})" if r.via else f"{r.name}: {STATE_TEXT.get(r.state, r.state)}"
                for r in rows
                if r.state != "available"
            ] or ["No phone connected"]
        # Windows limits tooltips to 127 characters.
        return ("scrcpy-autolaunch\n" + "\n".join(lines))[:127]

    # ── menu ─────────────────────────────────────────────────────────────────

    def _menu_items(self):
        Item, Menu = self.pystray.MenuItem, self.pystray.Menu
        if self.problem:
            yield Item(self.problem, None, enabled=False)
            yield Item("Open log", lambda *_: self._open(paths.log_file()))
            yield Menu.SEPARATOR
        else:
            yield from self._phone_items()
            yield Menu.SEPARATOR
        yield Item(
            "Audio",
            Menu(
                *(
                    Item(text, self._set_audio(mode), checked=self._audio_is(mode), radio=True)
                    for mode, text in AUDIO_MODES
                )
            ),
        )
        yield Item(
            "Force landscape",
            self._toggle_landscape,
            checked=lambda _: self.config.force_landscape,
        )
        yield Item(
            "Wi-Fi",
            Menu(
                Item("Pair new phone…", lambda *_: self._dialog("pair")),
                Item("Connect to address…", lambda *_: self._dialog("connect")),
                Item("Manage Wi-Fi phones…", lambda *_: self._dialog("devices")),
                Menu.SEPARATOR,
                Item("Disconnect all Wi-Fi phones", lambda *_: self._background(self._disconnect_all)),
            ),
            enabled=self.adb is not None,
        )
        yield Item(
            "Settings",
            Menu(
                Item("Auto-launch on USB", self._toggle("auto_usb"), checked=lambda _: self.config.auto_usb),
                Item(
                    "Auto-launch on Wi-Fi",
                    self._toggle("auto_wireless"),
                    checked=lambda _: self.config.auto_wireless,
                ),
                Item(
                    "Keep Wi-Fi connected after closing the window",
                    self._toggle("keep_wifi_connected"),
                    checked=lambda _: self.config.keep_wifi_connected,
                ),
                Item(
                    "Show sidebar next to the window",
                    self._toggle_sidebar,
                    checked=lambda _: self.config.show_sidebar,
                ),
                Item(
                    "Hide phone keyboard while mirroring",
                    self._toggle("hide_phone_keyboard", restart=True),
                    checked=lambda _: self.config.hide_phone_keyboard,
                ),
                Item("Start at login", self._toggle_autostart, checked=lambda _: autostart.is_enabled()),
                Menu.SEPARATOR,
                Item("Open log", lambda *_: self._open(paths.log_file())),
                Item("Open settings folder", lambda *_: self._open(paths.config_dir())),
            ),
        )
        yield Menu.SEPARATOR
        yield Item("Quit", self.quit)

    def _phone_items(self):
        Item, Menu = self.pystray.MenuItem, self.pystray.Menu
        rows = self.rows()
        if not rows:
            yield Item("No phones yet: plug one in with USB debugging on", None, enabled=False)
            yield Item("Pair a phone over Wi-Fi…", lambda *_: self._dialog("pair"))
            return
        for r in rows:
            if r.state == "mirroring":
                sub = []
                if IS_WINDOWS:
                    sub.append(Item("Show window", self._show(r.hw_id), default=True))
                sub.append(Item("Stop mirroring", self._stop(r.hw_id)))
                sub.append(Item("Open shell", self._shell(r.hw_id)))
                if r.wifi_serial:
                    sub.append(Item("Disconnect Wi-Fi", self._disconnect(r.wifi_serial)))
                yield Item(f"{r.name}: mirroring ({r.via_text})", Menu(*sub))
            elif r.state == "connected":
                yield Item(f"Mirror {r.name} ({r.via_text})", self._mirror(r.hw_id))
            elif r.state == "available":
                yield Item(f"Connect and mirror {r.name} (Wi-Fi)", self._connect_and_mirror(r.hw_id))
            elif r.state == "connecting":
                yield Item(f"{r.name}: connecting…", None, enabled=False)
            else:
                yield Item(f"{r.name}: {STATE_TEXT.get(r.state, r.state)}", None, enabled=False)

    # ── phone actions ────────────────────────────────────────────────────────

    def _mirror(self, hw_id: str):
        def action(*_):
            if self.watcher:
                self._background(lambda: log.info("Mirror %s: %s", hw_id, self.watcher.mirror(hw_id)))

        return action

    def _show(self, hw_id: str):
        def action(*_):
            pid = self.watcher.session_pid(hw_id) if self.watcher else None
            if pid is None or not focus_process_window(pid):
                log.info("No scrcpy window found for %s", hw_id)

        return action

    def _shell(self, hw_id: str):
        def action(*_):
            try:
                if self.watcher and not self.watcher.open_shell(hw_id):
                    self.notify("The phone isn't connected.")
            except OSError as exc:
                self.notify(f"Could not open a terminal: {exc}")

        return action

    def _stop(self, hw_id: str):
        def action(*_):
            if self.watcher:
                self.watcher.stop_mirroring(hw_id)

        return action

    def _disconnect(self, serial: str):
        def action(*_):
            assert self.adb is not None
            log.info("Disconnecting %s", serial)
            self._background(lambda: (self.adb.disconnect(serial), self.refresh()))

        return action

    def _connect_and_mirror(self, hw_id: str):
        """Clicking a phone means 'show me this phone': connect over Wi-Fi, then mirror,
        whatever the Wi-Fi auto-launch setting is."""

        def action(*_):
            k = self.known.get(hw_id)
            if k is None or self.adb is None or self.watcher is None or hw_id in self._connecting:
                return

            def work():
                self._connecting.add(hw_id)
                self.refresh()
                try:
                    ok, result = reconnect(self.adb, k, progress=lambda m: log.info("%s", m))
                finally:
                    self._connecting.discard(hw_id)
                if not ok:
                    log.warning("Could not connect to %s:\n%s", k.label, result)
                    # Notifications are easy to miss; show the details in a window.
                    self._dialog("devices", f"Could not connect to {k.label}.\n{result}")
                    self.refresh()
                    return
                self.known.remember(hw_id, address=result)
                log.info("Connected to %s at %s", k.label, result)
                # Wait for the watcher to pick the device up, then open the window.
                for _ in range(20):
                    outcome = self.watcher.mirror(hw_id)
                    if outcome != "not connected":
                        log.info("Mirror %s: %s", k.label, outcome)
                        break
                    time.sleep(0.25)
                self.refresh()

            self._background(work)

        return action

    # ── settings actions ─────────────────────────────────────────────────────

    def _toggle(self, key: str, restart: bool = False):
        def action(*_):
            setattr(self.config, key, not getattr(self.config, key))
            self.config.save()
            log.info("Setting %s = %s", key, getattr(self.config, key))
            self.icon.update_menu()
            if restart:
                self._restart_sessions()

        return action

    def _toggle_sidebar(self, *_):
        self.config.show_sidebar = not self.config.show_sidebar
        self.config.save()
        log.info("Setting show_sidebar = %s", self.config.show_sidebar)
        self.icon.update_menu()
        if self.watcher:
            self.watcher.apply_sidebar_setting()

    def _toggle_landscape(self, *_):
        self.config.force_landscape = not self.config.force_landscape
        self.config.save()
        log.info("Setting force_landscape = %s", self.config.force_landscape)
        self.icon.update_menu()
        if self.watcher:
            self.watcher.apply_landscape_setting()  # applies to open windows right away

    def _audio_is(self, mode: str):
        return lambda _item: self.config.audio == mode

    def _set_audio(self, mode: str):
        def action(*_):
            if self.config.audio == mode:
                return
            self.config.audio = mode
            self.config.save()
            log.info("Setting audio = %s", mode)
            self.icon.update_menu()
            self._restart_sessions()

        return action

    def _restart_sessions(self) -> None:
        if self.watcher:
            self._background(self.watcher.restart_sessions)

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

    def _disconnect_all(self) -> None:
        assert self.adb is not None
        log.info("Disconnect all: %s", self.adb.disconnect())
        self.refresh()

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
    theme.match_tray_menu_theme()
    app = TrayApp(config, adb, scrcpy, version, problem)
    log.info("Tray started (Python %s)", sys.version.split()[0])
    app.run()
    log.info("Tray stopped")
