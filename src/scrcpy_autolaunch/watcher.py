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
    ):
        self.config = config
        self.adb = adb
        self.scrcpy = scrcpy
        self.scrcpy_version = scrcpy_version
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
                if self._auto_enabled(dev):
                    self._launch(dev)

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
        args = [self.scrcpy, "-s", dev.serial, *self.config.scrcpy_args]
        if dev.transport == WIRELESS:
            args += self.config.wireless_extra_args
        if self.scrcpy_version is not None and self.scrcpy_version < (2, 0):
            # scrcpy 1.x has no audio support (and no --no-audio flag).
            args = [a for a in args if not a.startswith(("--no-audio", "--audio"))]
        return args

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
            if code != 0 and self._clock() - s.started < QUICK_FAIL_SECONDS:
                self._notify(f"scrcpy failed for {s.device.label} (exit code {code}). See the log.")
        return changed

    @staticmethod
    def _pump_output(proc: subprocess.Popen, serial: str) -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log.info("  scrcpy[%s] %s", serial, line)
