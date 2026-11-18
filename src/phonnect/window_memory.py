"""Where each phone's mirror window was, so it reopens there at the same size.

Saved per phone and per orientation (portrait / landscape), plus the desktop-mode window.
Only the position and the height are kept: given just a height, scrcpy works out the width
from the phone's picture, so a reopened window never has black bars.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from phonnect import paths
from phonnect.osutil import point_on_a_screen

log = logging.getLogger(__name__)

MIN_HEIGHT = 200  # smaller than this is a mistake (or a minimized window), not a choice


class WindowMemory:
    def __init__(self, path: Path | None = None):
        self.path = path or paths.state_dir() / "windows.json"
        self._lock = threading.Lock()
        self._data: dict[str, dict] = self._load()

    @staticmethod
    def key(hw_id: str, desktop: bool = False) -> str:
        return f"{hw_id}/desktop" if desktop else hw_id

    def remember(self, key: str, x: int, y: int, width: int, height: int) -> bool:
        """Save a window's content area. Returns True if anything changed."""
        if height < MIN_HEIGHT or width <= 0:
            return False
        orientation = "landscape" if width > height else "portrait"
        entry = {"x": int(x), "y": int(y), "height": int(height)}
        with self._lock:
            phone = self._data.setdefault(key, {})
            if phone.get(orientation) == entry:
                return False
            phone[orientation] = entry
            self._persist()
        return True

    def get(self, key: str, landscape: bool) -> dict | None:
        with self._lock:
            phone = self._data.get(key) or {}
            entry = phone.get("landscape" if landscape else "portrait")
            return dict(entry) if isinstance(entry, dict) else None

    def launch_args(self, key: str, landscape: bool, on_screen=point_on_a_screen) -> list[str]:
        """scrcpy arguments that reopen the window where it was ([] if nothing is saved)."""
        entry = self.get(key, landscape)
        if not entry or int(entry.get("height", 0)) < MIN_HEIGHT:
            return []
        args = [f"--window-height={int(entry['height'])}"]
        x, y = int(entry.get("x", 0)), int(entry.get("y", 0))
        # A monitor that's gone or rearranged: let scrcpy pick the position, keep the size.
        if on_screen(x + 20, y + 20):
            args += [f"--window-x={x}", f"--window-y={y}"]
        return args

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
            tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            log.warning("Could not save %s: %s", self.path, exc)


def fitted_width(client_width: int, client_height: int, video_width: int, video_height: int) -> int | None:
    """The window width that removes black bars at the current height, or None if it already fits."""
    if min(client_width, client_height, video_width, video_height) <= 0:
        return None
    width = round(client_height * video_width / video_height)
    return width if abs(width - client_width) >= 2 else None
