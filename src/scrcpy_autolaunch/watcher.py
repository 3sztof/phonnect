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

from scrcpy_autolaunch.adb import EMULATOR, USB, WIRELESS, Adb, Device
from scrcpy_autolaunch.config import Config
from scrcpy_autolaunch.osutil import NO_WINDOW

log = logging.getLogger(__name__)

# A scrcpy that dies this quickly with an error almost certainly failed to start.
QUICK_FAIL_SECONDS = 5.0

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
        self.rotation = None  # rotation.RotationKeeper, optional (set by the tray)
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
        self._warned_usb_off: set[str] = set()

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
                if self._auto_enabled(dev):
                    self._launch(dev)
                if self.rotation is not None and hw not in self.sessions and self.rotation.has_saved(hw):
                    # Left in landscape by a session that ended while the phone was unreachable.
                    self.rotation.restore(hw)
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
            if hw_id in self.sessions:
                return "already mirroring"
            for dev in sorted(self.devices.values(), key=lambda d: d.transport != USB):
                if self.hw_ids.get(dev.serial, dev.serial) == hw_id and dev.online:
                    ok = self._launch(dev)
                    self._on_change()
                    return "started" if ok else "could not start scrcpy"
        return "not connected"

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
        if self.rotation is not None:
            self.rotation.restore(hw_id)
        self._on_change()
        return True

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
        with self._lock:
            active = [hw for hw, s in self.sessions.items() if s.proc.poll() is None]
        for hw in active:
            if self.config.force_landscape:
                self.rotation.lock_landscape(hw)
            else:
                self.rotation.restore(hw)

    def restore_all_rotation(self) -> None:
        """On quit: put every phone we rotated back the way it was."""
        if self.rotation is None:
            return
        with self._lock:
            hws = list(self.sessions)
        for hw in hws:
            self.rotation.restore(hw)
        self.rotation.flush()

    def snapshot(self) -> list[tuple[Device, bool]]:
        """Connected devices and whether each phone is currently being mirrored."""
        with self._lock:
            active = {hw for hw, s in self.sessions.items() if s.proc.poll() is None}
            return [
                (d, self.hw_ids.get(d.serial, d.serial) in active)
                for d in sorted(self.devices.values(), key=lambda d: d.transport != USB)
            ]

    # ── helpers ──────────────────────────────────────────────────────────────

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

        self.sessions[hw] = Session(device=dev, hw_id=hw, proc=proc, started=self._clock())
        log.info("scrcpy started for %s (pid %s): %s", dev.label, proc.pid, " ".join(args[1:]))
        if self.config.force_landscape and self.rotation is not None:
            self.rotation.lock_landscape(hw)
        if proc.stdout is not None:
            threading.Thread(
                target=self._pump_output, args=(proc, dev.serial), name="scrcpy-output", daemon=True
            ).start()
        return True

    def _reap(self) -> bool:
        changed = False
        for hw, s in list(self.sessions.items()):
            code = s.proc.poll()
            if code is None:
                continue
            del self.sessions[hw]
            changed = True
            log.info("scrcpy exited for %s (code %s)", s.device.label, code)
            if self.rotation is not None:
                self.rotation.restore(hw)
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
