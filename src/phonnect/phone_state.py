"""Temporary changes to phone settings, always put back afterwards.

Used for "Force landscape" (screen rotation) and the content-size slider
(display density). Before the first change, the phone's own value is saved to
a JSON file. It's restored when the window closes, the setting is switched
back, or the app quits. If the phone was unreachable at that moment (unplugged
mid-session), the saved value stays on disk and is restored the next time the
phone connects.

All adb calls run on one worker thread per keeper, so a change and a restore
never race.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Callable
from pathlib import Path

from phonnect import paths
from phonnect.adb import LANDSCAPE

log = logging.getLogger(__name__)


class PhoneSettingKeeper:
    """Subclasses define read(), write() and describe() for one phone setting."""

    what = "setting"
    filename = "setting.json"

    def __init__(self, adb, serial_for: Callable[[str], str | None], path: Path | None = None, threaded: bool = True):
        self.adb = adb
        self.serial_for = serial_for  # hardware id -> an online adb serial, or None
        self.path = path or paths.state_dir() / self.filename
        self._lock = threading.Lock()
        self._saved: dict[str, dict] = self._load()
        self._q: queue.Queue = queue.Queue()
        self._threaded = threaded
        if threaded:
            threading.Thread(target=self._worker, name=self.what, daemon=True).start()

    # ── to implement ─────────────────────────────────────────────────────────

    def read(self, serial: str) -> dict | None:
        raise NotImplementedError

    def write(self, serial: str, state: dict) -> bool:
        raise NotImplementedError

    def describe(self, state: dict) -> str:
        return str(state)

    # ── public API (non-blocking) ────────────────────────────────────────────

    def change(self, hw_id: str, target: Callable[[dict], dict], label: str) -> None:
        """Save the phone's current value (once), then apply target(saved)."""
        self._submit(self._do_change, hw_id, target, label)

    def restore(self, hw_id: str) -> None:
        self._submit(self._do_restore, hw_id)

    def has_saved(self, hw_id: str) -> bool:
        with self._lock:
            return hw_id in self._saved

    def saved(self, hw_id: str) -> dict | None:
        with self._lock:
            return self._saved.get(hw_id)

    def flush(self) -> None:
        """Wait until queued changes are done (used on quit and in tests)."""
        if self._threaded:
            self._q.join()

    # ── internals ────────────────────────────────────────────────────────────

    def _submit(self, fn, *args) -> None:
        if self._threaded:
            self._q.put((fn, args))
        else:
            fn(*args)

    def _worker(self) -> None:
        while True:
            fn, args = self._q.get()
            try:
                fn(*args)
            except Exception:
                log.exception("Changing the %s failed", self.what)
            finally:
                self._q.task_done()

    def _do_change(self, hw_id: str, target: Callable[[dict], dict], label: str) -> None:
        serial = self.serial_for(hw_id)
        if serial is None:
            return
        with self._lock:
            saved = self._saved.get(hw_id)
        if saved is None:
            saved = self.read(serial)
            if saved is None:
                log.warning("Could not read the %s of %s; leaving it unchanged", self.what, serial)
                return
            with self._lock:
                self._saved[hw_id] = saved
                self._persist()
        if self.write(serial, target(saved)):
            log.info("Set %s on %s to %s (will restore %s afterwards)", self.what, serial, label, self.describe(saved))
        else:
            log.warning("Could not change the %s on %s", self.what, serial)

    def _do_restore(self, hw_id: str) -> None:
        with self._lock:
            saved = self._saved.get(hw_id)
        if saved is None:
            return
        serial = self.serial_for(hw_id)
        if serial is None:
            log.info("Phone %s is gone; its %s will be restored when it reconnects", hw_id, self.what)
            return
        if self.write(serial, saved):
            log.info("Restored %s on %s (%s)", self.what, serial, self.describe(saved))
            with self._lock:
                self._saved.pop(hw_id, None)
                self._persist()
        else:
            log.warning("Could not restore the %s on %s; will retry on reconnect", self.what, serial)

    def _load(self) -> dict[str, dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _persist(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._saved, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            log.warning("Could not save %s: %s", self.path, exc)


class RotationKeeper(PhoneSettingKeeper):
    what = "screen rotation"
    filename = "rotation.json"

    def read(self, serial):
        return self.adb.rotation_state(serial)

    def write(self, serial, state):
        return self.adb.apply_rotation(serial, state)

    def describe(self, state):
        if state.get("method") == "wm":
            return f"{'auto-rotate' if state['mode'] == 'free' else 'locked'}, rotation {state['rotation']}"
        return f"auto-rotate={state.get('accelerometer_rotation')}, rotation {state.get('user_rotation')}"

    def lock_landscape(self, hw_id: str) -> None:
        self.change(hw_id, lambda saved: LANDSCAPE[saved["method"]], "landscape")


MIN_SCALE, MAX_SCALE = 50, 100


class DensityKeeper(PhoneSettingKeeper):
    """Content size: a lower display density fits more on the screen."""

    what = "display density"
    filename = "density.json"

    def read(self, serial):
        return self.adb.density_state(serial)

    def write(self, serial, state):
        return self.adb.apply_density(serial, state)

    def describe(self, state):
        if state.get("override"):
            return f"{state['override']} dpi"
        return f"default ({state.get('physical')} dpi)"

    @staticmethod
    def scaled(saved: dict, percent: int) -> dict:
        base = saved.get("override") or saved["physical"]
        return {"physical": saved["physical"], "override": max(72, round(base * percent / 100))}

    def set_scale(self, hw_id: str, percent: int) -> None:
        """percent of the phone's own content size: 100 = unchanged, 50 = twice as much fits."""
        percent = max(MIN_SCALE, min(MAX_SCALE, int(percent)))
        if percent >= MAX_SCALE:
            self.restore(hw_id)
        else:
            self.change(hw_id, lambda saved: self.scaled(saved, percent), f"{percent}%")


class OverlayDisplayKeeper(PhoneSettingKeeper):
    """Desktop mode: a simulated second screen (Developer options > Simulate secondary displays).

    Android's desktop launches apps on it, unlike on scrcpy's own virtual displays, where the
    desktop's taskbar can't open apps on current Pixels (scrcpy issues #6699, #7048). While it's
    on, the phone shows a small preview of that screen. Removed when the desktop window closes.
    """

    what = "simulated second screen"
    filename = "overlay-display.json"
    SETTING = "overlay_display_devices"

    def read(self, serial):
        ok, value = self.adb.global_setting(serial, self.SETTING)
        return {"value": value} if ok else None

    def write(self, serial, state):
        return self.adb.put_global_setting(serial, self.SETTING, state.get("value"))

    def describe(self, state):
        return state.get("value") or "none"

    def show(self, hw_id: str, spec: str) -> None:
        """spec: WIDTHxHEIGHT/DPI, e.g. 1920x1080/160."""
        self.change(hw_id, lambda saved: {"value": spec}, spec)
