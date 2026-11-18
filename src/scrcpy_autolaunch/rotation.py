"""Force the phone into landscape while it is mirrored, and put it back afterwards.

The original rotation settings are saved to rotation.json before the first change.
If the phone is unplugged mid-session, adb can't reach it to undo the change, so
the saved state stays on disk and is restored the next time the phone connects.

All adb calls run on one worker thread, so a lock and a restore never race.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from pathlib import Path
from typing import Callable

from scrcpy_autolaunch import paths
from scrcpy_autolaunch.adb import LANDSCAPE

log = logging.getLogger(__name__)


class RotationKeeper:
    def __init__(self, adb, serial_for: Callable[[str], str | None], path: Path | None = None, threaded: bool = True):
        self.adb = adb
        self.serial_for = serial_for  # hardware id -> an online adb serial, or None
        self.path = path or paths.state_dir() / "rotation.json"
        self._lock = threading.Lock()
        self._saved: dict[str, dict] = self._load()
        self._q: queue.Queue = queue.Queue()
        self._threaded = threaded
        if threaded:
            threading.Thread(target=self._worker, name="rotation", daemon=True).start()

    # ── public API (non-blocking) ────────────────────────────────────────────

    def lock_landscape(self, hw_id: str) -> None:
        self._submit(self._do_lock, hw_id)

    def restore(self, hw_id: str) -> None:
        self._submit(self._do_restore, hw_id)

    def has_saved(self, hw_id: str) -> bool:
        with self._lock:
            return hw_id in self._saved

    def flush(self) -> None:
        """Wait until queued changes are done (used on quit and in tests)."""
        if self._threaded:
            self._q.join()

    # ── internals ────────────────────────────────────────────────────────────

    def _submit(self, fn, hw_id: str) -> None:
        if self._threaded:
            self._q.put((fn, hw_id))
        else:
            fn(hw_id)

    def _worker(self) -> None:
        while True:
            fn, hw_id = self._q.get()
            try:
                fn(hw_id)
            except Exception:
                log.exception("Rotation change failed for %s", hw_id)
            finally:
                self._q.task_done()

    def _do_lock(self, hw_id: str) -> None:
        serial = self.serial_for(hw_id)
        if serial is None:
            return
        with self._lock:
            saved = self._saved.get(hw_id)
        if saved is None:
            saved = self.adb.rotation_state(serial)
            if saved is None:
                log.warning("Could not read the screen rotation of %s; not forcing landscape", serial)
                return
            with self._lock:
                self._saved[hw_id] = saved
                self._persist()
        if self.adb.apply_rotation(serial, LANDSCAPE[saved["method"]]):
            log.info("Forced landscape on %s (will restore %s afterwards)", serial, _describe(saved))
        else:
            log.warning("Could not force landscape on %s", serial)

    def _do_restore(self, hw_id: str) -> None:
        with self._lock:
            saved = self._saved.get(hw_id)
        if saved is None:
            return
        serial = self.serial_for(hw_id)
        if serial is None:
            log.info("Phone %s is gone; its screen rotation will be restored when it reconnects", hw_id)
            return
        if self.adb.apply_rotation(serial, saved):
            log.info("Restored screen rotation on %s (%s)", serial, _describe(saved))
            with self._lock:
                self._saved.pop(hw_id, None)
                self._persist()
        else:
            log.warning("Could not restore the screen rotation on %s; will retry on reconnect", serial)

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


def _describe(state: dict) -> str:
    if state.get("method") == "wm":
        return f"{'auto-rotate' if state['mode'] == 'free' else 'locked'}, rotation {state['rotation']}"
    return f"auto-rotate={state.get('accelerometer_rotation')}, rotation {state.get('user_rotation')}"
