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
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable

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
        self.control: tuple[str, str] | None = None  # (address, token) of the control server
        self.style_windows = False  # match scrcpy's title bar to the OS theme (set by the tray)
        self.on_quit: Callable[[], None] | None = None  # how a "quit" control request ends the app
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
            self._reap()
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

    def open_desktop(self, hw_id: str) -> str:
        """Open the phone's desktop mode on a second, PC-sized virtual screen."""
        from phonnect.osutil import focus_process_window

        with self._lock:
            existing = self.desktops.get(hw_id)
            if existing is not None and existing.poll() is None:
                focus_process_window(existing.pid)
                return "already open"
            if self.scrcpy_version is not None and self.scrcpy_version < (3, 0):
                return "desktop mode needs scrcpy 3.0 or newer"
            serial = self.online_serial(hw_id)
            if serial is None:
                return "not connected"
            dev = self.devices[serial]
            args = self.build_desktop_args(dev)
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
                return f"could not start scrcpy: {exc}"
            self.desktops[hw_id] = proc
            log.info("Desktop mode started for %s (pid %s): %s", dev.label, proc.pid, " ".join(args[1:]))
        if proc.stdout is not None:
            threading.Thread(
                target=self._pump_output, args=(proc, f"{serial} desktop"), name="desktop-output", daemon=True
            ).start()
        if self.style_windows:
            threading.Thread(target=self._style_window, args=(proc.pid,), name="style", daemon=True).start()
        return "started"

    def build_desktop_args(self, dev: Device) -> list[str]:
        name = dev.label.rsplit(" (", 1)[0]
        # The main window keeps the audio; size limits would shrink the desktop.
        base = [a for a in self.config.scrcpy_args if a != "--no-audio" and not a.startswith(("--max-size", "-m"))]
        args = [
            self.scrcpy, "-s", dev.serial,
            f"--new-display={self.config.desktop_display}",
            "--no-audio",
            f"--window-title={name} desktop",
            *base,
        ]  # fmt: skip
        if self.config.hide_phone_keyboard and (self.scrcpy_version is None or self.scrcpy_version >= (2, 4)):
            args.append("--keyboard=uhid")
        args += self._mouse_args(args)
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
        """On quit: put back everything we changed on any phone, and close sidebars."""
        with self._lock:
            sessions = list(self.sessions.values())
        for s in sessions:
            self._close_sidebar(s)
            self._restore_phone_settings(s.hw_id)
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
            return {"ok": True, "force_landscape": self.config.force_landscape, "content_scale": self.config.content_scale}
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
                names = {hw.lower(), *(d.serial.lower() for d in devs), *(d.model.replace("_", " ").lower() for d in devs)}
                if target in names:
                    return {"ok": True, "result": self.mirror(hw)}
            return {"ok": False, "error": f"no connected phone matches {target!r}"}
        if cmd == "open_desktop":
            result = self.open_desktop(str(msg.get("hw", "")))
            return {"ok": result in ("started", "already open"), "result": result}
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
        return [k for k in (self.rotation, self.density) if k is not None]

    def _apply_phone_settings(self, hw: str) -> None:
        if self.config.force_landscape and self.rotation is not None:
            self.rotation.lock_landscape(hw)
        if self.config.content_scale < 100 and self.density is not None:
            self.density.set_scale(hw, self.config.content_scale)

    def _restore_phone_settings(self, hw: str) -> None:
        for k in self._keepers():
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
        if self.config.hide_phone_keyboard and not user_set_keyboard:
            if self.scrcpy_version is None or self.scrcpy_version >= (2, 4):  # --keyboard was added in 2.4
                args.append("--keyboard=uhid")
        if self.scrcpy_version is not None and self.scrcpy_version < (2, 0):
            # scrcpy 1.x has no audio support (and no --no-audio flag).
            args = [a for a in args if not a.startswith(("--no-audio", "--audio"))]
        return args

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
            for hw, s in active:
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
        if proc.stdout is not None:
            threading.Thread(
                target=self._pump_output, args=(proc, dev.serial), name="scrcpy-output", daemon=True
            ).start()
        return True

    def _reap(self) -> bool:
        changed = False
        for hw, proc in list(self.desktops.items()):
            code = proc.poll()
            if code is not None:
                del self.desktops[hw]
                log.info("Desktop mode closed for %s (code %s)", hw, code)
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
            if dev.transport == WIRELESS and self.config.auto_usb and self.adb.usb_debugging_enabled(dev.serial) is False:
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
    def _pump_output(proc: subprocess.Popen, serial: str) -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log.info("  scrcpy[%s] %s", serial, line)
