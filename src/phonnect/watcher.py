"""Watch adb for devices and start scrcpy when one connects.

Rules:
- A device that appears (or becomes authorized) gets a scrcpy window, if
  auto-launch is on for its transport (USB / Wi-Fi).
- Closing the window does not relaunch it. The device must disappear from
  adb (unplug, Wi-Fi drop) and come back first, or the user clicks "Mirror now".
- One window per phone: the same phone seen over USB and Wi-Fi is deduplicated
  by its hardware serial number, preferring USB.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from phonnect.adb import EMULATOR, USB, WIRELESS, Adb, Device
from phonnect.config import Config
from phonnect.osutil import NO_WINDOW, gui_python, open_terminal

log = logging.getLogger(__name__)

# A scrcpy that dies this quickly with an error almost certainly failed to start.
QUICK_FAIL_SECONDS = 5.0

# Mouse buttons in scrcpy's --mouse-bind order, with their default action.
MOUSE_DEFAULTS = {"right": "app", "middle": "home", "back": "back", "forward": "recents"}
MOUSE_ACTIONS = {"app": "+", "back": "b", "home": "h", "recents": "s", "notifications": "n", "nothing": "-"}

STATE_HINTS = {
    "unauthorized": "accept the 'Allow USB debugging' prompt on the phone",
    "no permissions": "adb lacks USB permissions; see the Linux section of the README (udev rules)",
    "offline": "the device is not responding; try replugging it",
}


@dataclass
class Session:
    device: Device
    hw_id: str
    proc: subprocess.Popen
    started: float
    sidebar: subprocess.Popen | None = None


@dataclass
class TrackedWindow:
    """A scrcpy window whose place is remembered (and black bars trimmed once it opens)."""

    key: str  # WindowMemory key: the phone, or the phone's desktop
    proc: subprocess.Popen
    video: tuple[int, int] | None = None  # the picture's size, from scrcpy's "Texture: WxH"
    trimmed: bool = False
    checks: int = 0


TEXTURE_RE = re.compile(r"Texture: (\d+)x(\d+)")
NEW_DISPLAY_RE = re.compile(r"New display: \S+ \(id=(\d+)\)")
DISPLAY_RE = re.compile(r"--display-id=(\d+)\s+\((\d+x\d+)\)")


def parse_display_list(text: str) -> dict[int, str]:
    """`scrcpy --list-displays` output -> {display id: "WIDTHxHEIGHT"}."""
    return {int(m.group(1)): m.group(2) for m in DISPLAY_RE.finditer(text)}


class Watcher:
    def __init__(
        self,
        config: Config,
        adb: Adb,
        scrcpy: str,
        scrcpy_version: tuple[int, int] | None = None,
        on_change: Callable[[], None] | None = None,
        notify: Callable[[str], None] | None = None,
        popen: Callable[..., subprocess.Popen] = subprocess.Popen,
        clock: Callable[[], float] = time.monotonic,
        known=None,
    ):
        self.config = config
        self.adb = adb
        self.scrcpy = scrcpy
        self.scrcpy_version = scrcpy_version
        self.known = known  # wireless.KnownDevices, optional
        self.rotation = None  # phone_state.RotationKeeper, optional (set by the tray)
        self.density = None  # phone_state.DensityKeeper, optional (set by the tray)
        self.overlay = None  # phone_state.OverlayDisplayKeeper, optional: desktop mode's second screen
        self.windows = None  # window_memory.WindowMemory, optional (set by the tray; Windows only)
        self.control: tuple[str, str] | None = None  # (address, token) of the control server
        self.style_windows = False  # match scrcpy's title bar to the OS theme (set by the tray)
        self.on_quit: Callable[[], None] | None = None  # how a "quit" control request ends the app
        self.on_show: Callable[[], None] | None = None  # the app was opened again: show where it is
        # Asks the user before desktop mode opens (set by the tray); returns whether to go ahead.
        self.confirm_desktop: Callable[[], bool] | None = None
        self._on_change = on_change or (lambda: None)
        self._notify = notify or (lambda msg: None)
        self._popen = popen
        self._clock = clock
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.devices: dict[str, Device] = {}
        self.hw_ids: dict[str, str] = {}
        self.sessions: dict[str, Session] = {}
        # Desktop mode windows (a second scrcpy on a virtual display), per phone.
        self.desktops: dict[str, subprocess.Popen] = {}
        self._desktop_opening: set[str] = set()
        # Windows whose place is remembered, by scrcpy's pid.
        self._tracked: dict[int, TrackedWindow] = {}
        self._warned_usb_off: set[str] = set()
        # Phones whose window the user closed: not auto-launched over Wi-Fi again
        # (adb may silently reconnect them via mDNS) until clicked or plugged in.
        self._user_closed: set[str] = set()

    # ── lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._thread = threading.Thread(target=self.run_forever, name="watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def run_forever(self) -> None:
        log.info("Watcher started (adb: %s, scrcpy: %s)", self.adb.path, self.scrcpy)
        try:
            self.adb.start_server()
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("adb start-server failed: %s", exc)
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("Unexpected error in watcher loop")
            try:
                self.follow_windows()
            except Exception:
                log.exception("Following the mirror windows failed")
            self._stop.wait(self.config.poll_interval)
        log.info("Watcher stopped")

    # ── main logic ───────────────────────────────────────────────────────────

    def tick(self) -> None:
        try:
            current = {d.serial: d for d in self.adb.devices() if d.transport != EMULATOR}
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("adb devices failed: %s", exc)
            return

        changed = False
        with self._lock:
            changed |= self._reap()

            for serial in list(self.devices):
                if serial not in current:
                    log.info("Device removed: %s", self.devices[serial].label)
                    del self.devices[serial]
                    self.hw_ids.pop(serial, None)
                    changed = True

            # USB first, so a phone on both transports mirrors over USB.
            for dev in sorted(current.values(), key=lambda d: d.transport != USB):
                old = self.devices.get(dev.serial)
                if old is not None and old.state == dev.state:
                    continue
                self.devices[dev.serial] = dev
                changed = True
                if not dev.online:
                    hint = STATE_HINTS.get(dev.state, "")
                    log.warning("Device %s is %s%s", dev.serial, dev.state, f": {hint}" if hint else "")
                    continue
                self.hw_ids[dev.serial] = self.adb.hardware_id(dev.serial)
                log.info("Device connected: %s [%s]", dev.label, dev.serial)
                hw = self.hw_ids[dev.serial]
                if dev.transport == USB:
                    self._user_closed.discard(hw)  # plugging in is a fresh request
                if self._auto_enabled(dev) and not (dev.transport == WIRELESS and hw in self._user_closed):
                    self._launch(dev)
                if hw not in self.sessions and any(k.has_saved(hw) for k in self._keepers()):
                    # Left changed by a session that ended while the phone was unreachable.
                    self._restore_phone_settings(hw)
                if self.known is not None:
                    threading.Thread(
                        target=self._learn, args=(dev, self.hw_ids[dev.serial]), name="learn", daemon=True
                    ).start()

        if changed:
            self._on_change()

    def mirror_now(self) -> int:
        """Open a window for every connected phone that doesn't have one."""
        started = 0
        with self._lock:
            self._reap()
            self._user_closed.clear()
            for dev in sorted(self.devices.values(), key=lambda d: d.transport != USB):
                if dev.online and self._launch(dev):
                    started += 1
        if started == 0:
            log.info("Mirror now: nothing to start (no device, or already mirroring)")
        self._on_change()
        return started

    def phones(self) -> list[tuple[str, list[Device], bool]]:
        """Connected phones as (hardware id, adb devices for it USB-first, being mirrored)."""
        with self._lock:
            # No reaping here: this runs on the tray's UI thread, and reaping a closed window
            # restores phone settings over adb. The watcher loop does it within a second.
            grouped: dict[str, list[Device]] = {}
            for d in sorted(self.devices.values(), key=lambda d: d.transport != USB):
                grouped.setdefault(self.hw_ids.get(d.serial, d.serial), []).append(d)
            return [
                (hw, devs, hw in self.sessions and self.sessions[hw].proc.poll() is None)
                for hw, devs in grouped.items()
            ]

    def mirror(self, hw_id: str) -> str:
        """Open a window for one phone. Returns a short result for the user."""
        with self._lock:
            self._reap()
            self._user_closed.discard(hw_id)
            if hw_id in self.sessions:
                return "already mirroring"
            for dev in sorted(self.devices.values(), key=lambda d: d.transport != USB):
                if self.hw_ids.get(dev.serial, dev.serial) == hw_id and dev.online:
                    ok = self._launch(dev)
                    self._on_change()
                    return "started" if ok else "could not start scrcpy"
        return "not connected"

    def open_desktop_and_report(self, hw_id: str) -> str:
        """open_desktop() for callers that don't wait: asks first, problems become a notification."""
        existing = self.desktops.get(hw_id)
        already_open = (existing is not None and existing.poll() is None) or hw_id in self._desktop_opening
        if already_open:
            pass  # just brought to the front: no questions
        elif self.confirm_desktop is not None:
            if not self.confirm_desktop():
                log.info("Desktop mode cancelled")
                return "cancelled"
        elif self.config.desktop_method == "overlay":
            self._notify(
                "Desktop mode is experimental, here be dragons. It uses a simulated second screen, so your "
                "phone shows a preview while it's open. If the preview stays after you close the window: "
                "Developer options > Simulate secondary displays > None (or restart the phone)."
            )
        else:
            self._notify(
                "Desktop mode is experimental: on current Pixels, apps may not open from its taskbar yet "
                "(a problem between Android and scrcpy)."
            )
        try:
            result = self.open_desktop(hw_id)
        except Exception as exc:
            log.exception("Desktop mode failed")
            result = f"failed: {exc}"
        if result not in ("started", "already open", "already opening", "cancelled"):
            self._notify(f"Desktop mode: {result}")
        return result

    def open_desktop(self, hw_id: str) -> str:
        """Open the phone's desktop mode in a second, PC-sized window.

        Preferred: a simulated second screen (overlay display), on which Android's desktop can
        launch apps. Fallback (or desktop_method "virtual"): scrcpy's own virtual display, where
        on current Pixels the taskbar shows but can't open apps.
        """
        from phonnect.osutil import focus_process_window

        with self._lock:
            existing = self.desktops.get(hw_id)
            if existing is not None and existing.poll() is None:
                focus_process_window(existing.pid)
                return "already open"
            if hw_id in self._desktop_opening:
                return "already opening"
            if self.scrcpy_version is not None and self.scrcpy_version < (3, 0):
                return "desktop mode needs scrcpy 3.0 or newer"
            serial = self.online_serial(hw_id)
            if serial is None:
                return "not connected"
            dev = self.devices[serial]
            self._desktop_opening.add(hw_id)
        try:
            display_id = None
            if self.config.desktop_method == "overlay" and self.overlay is not None:
                display_id = self._show_overlay_display(hw_id, serial)
            args = self.build_desktop_args(dev, display_id)
            child_env = dict(os.environ)
            child_env["ADB"] = self.adb.path
            try:
                proc = self._popen(
                    args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=child_env,
                    creationflags=NO_WINDOW,
                )
            except OSError as exc:
                log.error("Could not start desktop mode: %s", exc)
                if display_id is not None:
                    self.overlay.restore(hw_id)
                return f"could not start scrcpy: {exc}"
            with self._lock:
                self.desktops[hw_id] = proc
            log.info("Desktop mode started for %s (pid %s): %s", dev.label, proc.pid, " ".join(args[1:]))
        finally:
            with self._lock:
                self._desktop_opening.discard(hw_id)
        tracked = self._track(self.windows.key(hw_id, desktop=True), proc) if self.windows else None
        on_line = self._scrcpy_output(tracked)
        if display_id is None:  # scrcpy's virtual screen: its taskbar can't open apps, add the Apps panel
            on_line = self._desktop_output(on_line, dev, proc)
        if proc.stdout is not None:
            threading.Thread(
                target=self._pump_output,
                args=(proc, f"{serial} desktop", on_line),
                name="desktop-output",
                daemon=True,
            ).start()
        if self.style_windows:
            threading.Thread(target=self._style_window, args=(proc.pid,), name="style", daemon=True).start()
        return "started"

    def _show_overlay_display(self, hw_id: str, serial: str) -> int | None:
        """Turn on the simulated second screen and return its display id, or None (then: fallback)."""
        size = self.config.desktop_display.split("/", 1)[0]
        before = self._display_ids(serial)
        if before is None:
            return None
        assert self.overlay is not None
        self.overlay.show(hw_id, self.config.desktop_display)
        self.overlay.flush()
        deadline = self._clock() + 8
        while self._clock() < deadline:
            now = self._display_ids(serial) or {}
            new = [d for d, s in now.items() if d not in before and s == size] or [d for d in now if d not in before]
            if new:
                log.info("Simulated second screen for %s: display %s (%s)", serial, new[0], now[new[0]])
                return new[0]
            time.sleep(0.5)
        log.warning("The simulated second screen didn't appear on %s; using scrcpy's virtual display", serial)
        self.overlay.restore(hw_id)
        return None

    def _display_ids(self, serial: str) -> dict[int, str] | None:
        """The phone's displays as {id: "WIDTHxHEIGHT"}, from `scrcpy --list-displays`."""
        try:
            r = subprocess.run(
                [self.scrcpy, "-s", serial, "--list-displays"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=20,
                env=dict(os.environ, ADB=self.adb.path),
                creationflags=NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("Could not list the displays of %s: %s", serial, exc)
            return None
        return parse_display_list(r.stdout + r.stderr)

    def build_desktop_args(self, dev: Device, display_id: int | None = None) -> list[str]:
        name = dev.label.rsplit(" (", 1)[0]
        # The main window keeps the audio; size limits would shrink the desktop.
        base = [a for a in self.config.scrcpy_args if a != "--no-audio" and not a.startswith(("--max-size", "-m"))]
        screen = (
            f"--display-id={display_id}" if display_id is not None else f"--new-display={self.config.desktop_display}"
        )
        args = [
            self.scrcpy, "-s", dev.serial,
            screen,
            "--no-audio",
            f"--window-title={name} desktop",
            *base,
        ]  # fmt: skip
        if self.config.hide_phone_keyboard and (self.scrcpy_version is None or self.scrcpy_version >= (2, 4)):
            args.append("--keyboard=uhid")
        args += self._mouse_args(args)
        args += self._window_args(dev, args, desktop=True)
        return args

    def _mouse_args(self, args: list[str]) -> list[str]:
        """scrcpy's --mouse-bind from the mouse_buttons setting (right, middle, back, forward)."""
        if any(a.startswith("--mouse-bind") for a in args):
            return []  # set by the user in scrcpy_args
        if self.scrcpy_version is not None and self.scrcpy_version < (2, 5):  # --mouse-bind was added in 2.5
            return []
        chosen = self.config.mouse_buttons if isinstance(self.config.mouse_buttons, dict) else {}
        primary = ""
        for button, default in MOUSE_DEFAULTS.items():
            action = chosen.get(button, default)
            primary += MOUSE_ACTIONS.get(action, MOUSE_ACTIONS[default])
        # With Shift held: scrcpy's original shortcuts.
        return [f"--mouse-bind={primary}:bhsn"]

    def session_pid(self, hw_id: str) -> int | None:
        with self._lock:
            s = self.sessions.get(hw_id)
            return s.proc.pid if s is not None and s.proc.poll() is None else None

    def stop_mirroring(self, hw_id: str) -> bool:
        with self._lock:
            s = self.sessions.pop(hw_id, None)  # popped first: not reported as a failure
        if s is None:
            return False
        log.info("Stopping scrcpy for %s (requested from the tray)", s.device.label)
        s.proc.terminate()
        self._close_sidebar(s)
        self._restore_phone_settings(hw_id)
        self._closed_by_user(s)
        self._on_change()
        return True

    def _closed_by_user(self, s: Session) -> None:
        self._user_closed.add(s.hw_id)
        if s.device.transport == WIRELESS and not self.config.keep_wifi_connected:
            log.info("Window closed: disconnecting Wi-Fi for %s", s.device.label)
            threading.Thread(
                target=self._disconnect_quietly, args=(s.device.serial,), name="disconnect", daemon=True
            ).start()

    def _disconnect_quietly(self, serial: str) -> None:
        # Restores queued for this phone (rotation, density) need the connection: let them finish first.
        for k in self._keepers():
            k.flush()
        try:
            self.adb.disconnect(serial)
        except Exception as exc:
            log.warning("Could not disconnect %s: %s", serial, exc)

    def online_serial(self, hw_id: str) -> str | None:
        """An online adb serial for this phone (USB preferred), or None."""
        with self._lock:
            for d in sorted(self.devices.values(), key=lambda d: d.transport != USB):
                if d.online and self.hw_ids.get(d.serial, d.serial) == hw_id:
                    return d.serial
        return None

    def apply_landscape_setting(self) -> None:
        """Lock or restore rotation for open windows after the setting changed."""
        if self.rotation is None:
            return
        for hw in self._active():
            if self.config.force_landscape:
                self.rotation.lock_landscape(hw)
            else:
                self.rotation.restore(hw)

    def restore_all_phone_settings(self) -> None:
        """On quit: put back everything we changed on any phone, and close sidebars.

        Desktop windows close too: their simulated second screen is removed from the phone.
        """
        with self._lock:
            sessions = list(self.sessions.values())
            desktops = list(self.desktops.items())
            self.desktops.clear()
        for s in sessions:
            self._close_sidebar(s)
            self._restore_phone_settings(s.hw_id)
        for hw, proc in desktops:
            if proc.poll() is None:
                proc.terminate()
            if self.overlay is not None:
                self.overlay.restore(hw)
        for k in self._keepers():
            k.flush()

    def apply_content_scale(self) -> None:
        """Apply the content-size setting to open windows."""
        if self.density is None:
            return
        for hw in self._active():
            self.density.set_scale(hw, self.config.content_scale)

    def apply_sidebar_setting(self) -> None:
        with self._lock:
            for s in self.sessions.values():
                if s.proc.poll() is not None:
                    continue
                if self.config.show_sidebar and (s.sidebar is None or s.sidebar.poll() is not None):
                    self._spawn_sidebar(s)
                elif not self.config.show_sidebar:
                    self._close_sidebar(s)

    def open_shell(self, hw_id: str) -> bool:
        serial = self.online_serial(hw_id)
        if serial is None:
            return False
        open_terminal([self.adb.path, "-s", serial, "shell"])
        return True

    def handle_control(self, msg: dict) -> dict:
        """Requests from sidebar windows (see control.py)."""
        from phonnect.phone_state import MAX_SCALE, MIN_SCALE

        cmd = msg.get("cmd")
        if cmd == "state":
            return {
                "ok": True,
                "force_landscape": self.config.force_landscape,
                "content_scale": self.config.content_scale,
            }
        if cmd == "set_landscape":
            self.config.force_landscape = bool(msg.get("on"))
            self.config.save()
            log.info("Setting force_landscape = %s (from the sidebar)", self.config.force_landscape)
            self.apply_landscape_setting()
            self._on_change()
            return {"ok": True}
        if cmd == "set_scale":
            try:
                value = int(msg.get("value", MAX_SCALE))
            except (TypeError, ValueError):
                return {"ok": False, "error": "value must be a number"}
            self.config.content_scale = max(MIN_SCALE, min(MAX_SCALE, value))
            self.config.save()
            log.info("Setting content_scale = %s%% (from the sidebar)", self.config.content_scale)
            self.apply_content_scale()
            return {"ok": True, "content_scale": self.config.content_scale}
        if cmd == "mirror":
            target = str(msg.get("phone", "all")).lower()
            if target == "all":
                return {"ok": True, "started": self.mirror_now()}
            for hw, devs, _ in self.phones():
                names = {
                    hw.lower(),
                    *(d.serial.lower() for d in devs),
                    *(d.model.replace("_", " ").lower() for d in devs),
                }
                if target in names:
                    return {"ok": True, "result": self.mirror(hw)}
            return {"ok": False, "error": f"no connected phone matches {target!r}"}
        if cmd == "open_desktop":
            hw = str(msg.get("hw", ""))
            # Setting up the second screen takes a few seconds; don't keep the caller waiting.
            threading.Thread(target=self.open_desktop_and_report, args=(hw,), name="desktop", daemon=True).start()
            return {"ok": True, "result": "opening"}
        if cmd == "show":
            if self.on_show is None:
                return {"ok": False, "error": "show is not supported here"}
            self.on_show()
            return {"ok": True}
        if cmd == "quit":
            if self.on_quit is None:
                return {"ok": False, "error": "quit is not supported here"}
            threading.Thread(target=self.on_quit, name="quit", daemon=True).start()
            return {"ok": True}
        if cmd == "log":
            level = msg.get("level") if msg.get("level") in ("info", "warning", "error") else "info"
            getattr(log, level)("sidebar: %s", str(msg.get("message", ""))[:2000])
            return {"ok": True}
        return {"ok": False, "error": f"unknown command {cmd!r}"}

    def snapshot(self) -> list[tuple[Device, bool]]:
        """Connected devices and whether each phone is currently being mirrored."""
        with self._lock:
            active = {hw for hw, s in self.sessions.items() if s.proc.poll() is None}
            return [
                (d, self.hw_ids.get(d.serial, d.serial) in active)
                for d in sorted(self.devices.values(), key=lambda d: d.transport != USB)
            ]

    # ── helpers ──────────────────────────────────────────────────────────────

    def _active(self) -> list[str]:
        with self._lock:
            return [hw for hw, s in self.sessions.items() if s.proc.poll() is None]

    def _keepers(self) -> list:
        return [k for k in (self.rotation, self.density, self.overlay) if k is not None]

    def _apply_phone_settings(self, hw: str) -> None:
        if self.config.force_landscape and self.rotation is not None:
            self.rotation.lock_landscape(hw)
        if self.config.content_scale < 100 and self.density is not None:
            self.density.set_scale(hw, self.config.content_scale)

    def _restore_phone_settings(self, hw: str) -> None:
        desktop = self.desktops.get(hw)
        desktop_open = desktop is not None and desktop.poll() is None
        for k in self._keepers():
            if k is self.overlay and (desktop_open or hw in self._desktop_opening):
                continue  # the desktop window still needs its second screen
            k.restore(hw)

    def _spawn_sidebar(self, s: Session) -> None:
        if not (self.config.show_sidebar and self.control):
            return
        address, token = self.control
        cmd = [
            gui_python(), "-m", "phonnect", "_sidebar",
            "--serial", s.device.serial,
            "--hw", s.hw_id,
            "--pid", str(s.proc.pid),
            "--name", s.device.label.rsplit(" (", 1)[0],
        ]  # fmt: skip
        # The token goes in the environment, not on the command line other users could read.
        child_env = dict(os.environ)
        child_env["PHONNECT_CONTROL"] = f"{address} {token}"
        child_env["PHONNECT_APP_PID"] = str(os.getpid())  # the sidebar exits with the app
        child_env["ADB"] = self.adb.path
        try:
            s.sidebar = subprocess.Popen(
                cmd,
                env=child_env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=NO_WINDOW,
            )
        except OSError as exc:
            log.warning("Could not open the sidebar: %s", exc)

    @staticmethod
    def _close_sidebar(s: Session) -> None:
        if s.sidebar is not None and s.sidebar.poll() is None:
            s.sidebar.terminate()

    @staticmethod
    def _style_window(pid: int) -> None:
        """Match the scrcpy window's title bar to the OS light/dark mode (Windows)."""
        from phonnect import theme
        from phonnect.osutil import find_process_window

        for _ in range(50):  # the window appears a moment after the process starts
            hwnd = find_process_window(pid)
            if hwnd:
                theme.title_bar_hwnd(hwnd)
                return
            time.sleep(0.2)

    def _auto_enabled(self, dev: Device) -> bool:
        if dev.transport == USB:
            return self.config.auto_usb
        if dev.transport == WIRELESS:
            return self.config.auto_wireless
        return False

    def build_args(self, dev: Device) -> list[str]:
        # Audio is controlled by config.audio; drop a --no-audio left over from older configs.
        base = [a for a in self.config.scrcpy_args if a != "--no-audio"]
        args = [self.scrcpy, "-s", dev.serial, *base]
        if dev.transport == WIRELESS:
            args += [a for a in self.config.wireless_extra_args if a != "--no-audio"]
        args += self._audio_args()
        args += self._mouse_args(args)
        user_set_keyboard = any(a.startswith("--keyboard") or a in ("-K", "--hid-keyboard") for a in args)
        keyboard_supported = self.scrcpy_version is None or self.scrcpy_version >= (2, 4)  # added in 2.4
        if self.config.hide_phone_keyboard and not user_set_keyboard and keyboard_supported:
            args.append("--keyboard=uhid")
        if self.scrcpy_version is not None and self.scrcpy_version < (2, 0):
            # scrcpy 1.x has no audio support (and no --no-audio flag).
            args = [a for a in args if not a.startswith(("--no-audio", "--audio"))]
        args += self._window_args(dev, args)
        return args

    def _window_args(self, dev: Device, args: list[str], desktop: bool = False) -> list[str]:
        """Reopen the window where it was last time, unless scrcpy_args already place it."""
        if self.windows is None or any(
            a.startswith(("--window-x", "--window-y", "--window-h", "--window-w")) for a in args
        ):
            return []
        hw = self.hw_ids.get(dev.serial, dev.serial)
        landscape = desktop or self.config.force_landscape
        return self.windows.launch_args(self.windows.key(hw, desktop), landscape)

    # ── remembered window places (Windows) ───────────────────────────────────

    def _track(self, key: str, proc: subprocess.Popen) -> TrackedWindow | None:
        if self.windows is None:
            return None
        tracked = TrackedWindow(key=key, proc=proc)
        with self._lock:
            self._tracked[proc.pid] = tracked
        return tracked

    def follow_windows(self) -> None:
        """Remember where each window is, and trim black bars once the picture size is known."""
        if self.windows is None:
            return
        from phonnect.osutil import find_process_window, set_window_client_size, window_client_rect
        from phonnect.window_memory import fitted_width

        with self._lock:
            tracked = list(self._tracked.items())
        for pid, t in tracked:
            if t.proc.poll() is not None:
                with self._lock:
                    self._tracked.pop(pid, None)
                continue
            rect = window_client_rect(find_process_window(pid) or 0)
            if rect is None:
                continue
            x, y, width, height = rect
            if not t.trimmed and t.video is not None:
                t.checks += 1
                width_fit = fitted_width(width, height, *t.video)
                if width_fit is not None:
                    log.info("Trimming black bars: window %sx%s -> %sx%s", width, height, width_fit, height)
                    set_window_client_size(find_process_window(pid) or 0, width_fit, height)
                    continue  # remember it at the next look, once Windows has resized it
                t.trimmed = True
            if t.trimmed and self.windows.remember(t.key, x, y, width, height):
                log.debug("Window %s now at %s,%s %sx%s", t.key, x, y, width, height)

    def _desktop_output(self, on_line, dev: Device, proc: subprocess.Popen):
        """Also watch for scrcpy's "New display: ... (id=N)", then open the Apps panel for it."""

        def watch(line: str) -> None:
            on_line(line)
            if m := NEW_DISPLAY_RE.search(line):
                self._spawn_desktop_apps(dev, int(m.group(1)), proc)

        return watch

    def _spawn_desktop_apps(self, dev: Device, display_id: int, desktop: subprocess.Popen) -> None:
        if not self.control:
            return
        address, token = self.control
        cmd = [
            gui_python(), "-m", "phonnect", "_desktop_apps",
            "--serial", dev.serial,
            "--display", str(display_id),
            "--pid", str(desktop.pid),
            "--name", dev.label.rsplit(" (", 1)[0],
        ]  # fmt: skip
        child_env = dict(os.environ, ADB=self.adb.path, SCRCPY=self.scrcpy)
        child_env["PHONNECT_CONTROL"] = f"{address} {token}"
        try:
            subprocess.Popen(
                cmd,
                env=child_env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=NO_WINDOW,
            )
            log.info("Apps panel opened for the desktop (display %s)", display_id)
        except OSError as exc:
            log.warning("Could not open the Apps panel: %s", exc)

    def _scrcpy_output(self, tracked: TrackedWindow | None):
        def on_line(line: str) -> None:
            if tracked is not None and (m := TEXTURE_RE.search(line)):
                video = (int(m.group(1)), int(m.group(2)))
                if video != tracked.video:
                    tracked.video = video
                    tracked.trimmed = False  # rotated: check the bars again for the new shape

        return on_line

    def _audio_args(self) -> list[str]:
        mode = self.config.audio
        version = self.scrcpy_version
        if mode == "both":
            if version is None or version >= (2, 6):  # --audio-dup was added in 2.6
                return ["--audio-source=playback", "--audio-dup"]
            log.warning("Audio 'PC and phone' needs scrcpy 2.6 or newer; keeping audio on the phone")
            return ["--no-audio"]
        if mode == "pc":
            return []  # scrcpy's default: forward the whole output, phone goes silent
        return ["--no-audio"]

    def restart_sessions(self) -> int:
        """Reopen running scrcpy windows so changed settings take effect."""
        restarted = 0
        with self._lock:
            active = [(hw, s) for hw, s in self.sessions.items() if s.proc.poll() is None]
            for hw, s in active:
                del self.sessions[hw]  # not reaped: no "failed" notification for this exit
                s.proc.terminate()
                self._close_sidebar(s)
            for _hw, s in active:
                try:
                    s.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    s.proc.kill()
                dev = self.devices.get(s.device.serial)
                if dev is not None and dev.online:
                    log.info("Restarting scrcpy for %s to apply new settings", dev.label)
                    restarted += self._launch(dev)
        self._on_change()
        return restarted

    def _launch(self, dev: Device) -> bool:
        hw = self.hw_ids.get(dev.serial, dev.serial)
        existing = self.sessions.get(hw)
        if existing is not None and existing.proc.poll() is None:
            log.info("Already mirroring %s via %s", dev.label, existing.device.serial)
            return False

        args = self.build_args(dev)
        # Make scrcpy use the same adb binary, so two different adb versions
        # don't keep restarting each other's server.
        env = dict(os.environ, ADB=self.adb.path)
        try:
            proc = self._popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=NO_WINDOW,
            )
        except OSError as exc:
            log.error("Could not start scrcpy: %s", exc)
            self._notify(f"Could not start scrcpy: {exc}")
            return False

        session = Session(device=dev, hw_id=hw, proc=proc, started=self._clock())
        self.sessions[hw] = session
        log.info("scrcpy started for %s (pid %s): %s", dev.label, proc.pid, " ".join(args[1:]))
        self._apply_phone_settings(hw)
        self._spawn_sidebar(session)
        if self.style_windows:
            threading.Thread(target=self._style_window, args=(proc.pid,), name="style", daemon=True).start()
        tracked = self._track(hw, proc)
        if proc.stdout is not None:
            threading.Thread(
                target=self._pump_output,
                args=(proc, dev.serial, self._scrcpy_output(tracked)),
                name="scrcpy-output",
                daemon=True,
            ).start()
        return True

    def _reap(self) -> bool:
        changed = False
        for hw, proc in list(self.desktops.items()):
            code = proc.poll()
            if code is not None:
                del self.desktops[hw]
                log.info("Desktop mode closed for %s (code %s)", hw, code)
                if self.overlay is not None:
                    self.overlay.restore(hw)  # remove the simulated second screen
        for hw, s in list(self.sessions.items()):
            code = s.proc.poll()
            if code is None:
                continue
            del self.sessions[hw]
            changed = True
            log.info("scrcpy exited for %s (code %s)", s.device.label, code)
            self._close_sidebar(s)
            self._restore_phone_settings(hw)
            if code == 0:  # the user closed the window
                self._closed_by_user(s)
            if code != 0 and self._clock() - s.started < QUICK_FAIL_SECONDS:
                self._notify(f"scrcpy failed for {s.device.label} (exit code {code}). See the log.")
        return changed

    def _learn(self, dev: Device, hw: str) -> None:
        """Remember the phone's Wi-Fi IP and debugging port for later reconnects."""
        try:
            ip = self.adb.wifi_ip(dev.serial)
            port = self.adb.tls_port(dev.serial)
            enabled = self.adb.wifi_debugging_enabled(dev.serial)
            address = f"{ip}:{port}" if ip and port else ""
            if not address and dev.transport == WIRELESS and ":" in dev.serial and "._" not in dev.serial:
                address = dev.serial
            self.known.remember(hw, model=dev.model, address=address, ip=ip)
            if port:
                wifi = f"on (port {port})"
            else:
                wifi = {True: "on", False: "off", None: "unknown"}[enabled]
            log.info("Remembered %s: Wi-Fi IP %s, Wireless debugging %s", dev.label, ip or "unknown", wifi)
            if (
                dev.transport == WIRELESS
                and self.config.auto_usb
                and self.adb.usb_debugging_enabled(dev.serial) is False
            ):
                msg = (
                    f"USB debugging is off on {dev.label.rsplit(' (', 1)[0]}, so plugging it in won't open "
                    "a window. Turn it on in Settings > System > Developer options > USB debugging."
                )
                log.warning(msg)
                if hw not in self._warned_usb_off:
                    self._warned_usb_off.add(hw)
                    self._notify(msg)
            self._on_change()
        except Exception:
            log.exception("Could not read Wi-Fi details of %s", dev.serial)

    @staticmethod
    def _pump_output(proc: subprocess.Popen, serial: str, on_line=None) -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log.info("  scrcpy[%s] %s", serial, line)
                if on_line is not None:
                    try:
                        on_line(line)
                    except Exception:
                        log.debug("Reading scrcpy's output failed", exc_info=True)
