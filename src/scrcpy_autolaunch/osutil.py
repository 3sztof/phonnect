"""OS detection and process helpers shared by the rest of the package."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# Without this flag, every adb/scrcpy call from a windowless (pythonw) process
# would flash a console window on Windows.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def gui_python() -> str:
    """Interpreter that runs without a console window (pythonw on Windows)."""
    exe = Path(sys.executable)
    if IS_WINDOWS:
        pyw = exe.with_name("pythonw.exe")
        if pyw.is_file():
            return str(pyw)
    return str(exe)


def spawn_detached(cmd: list[str]) -> subprocess.Popen:
    """Start a process that outlives the caller and has no console attached."""
    kwargs: dict = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    if IS_WINDOWS:
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def focus_process_window(pid: int) -> bool:
    """Bring the visible top-level window of `pid` to the front (Windows only)."""
    if not IS_WINDOWS:
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(callback, 0)
    if not found:
        return False
    SW_RESTORE = 9
    user32.ShowWindow(found[0], SW_RESTORE)
    user32.SetForegroundWindow(found[0])
    return True


def open_path(path: Path) -> None:
    """Open a file or folder with the desktop's default application."""
    if IS_WINDOWS:
        os.startfile(path)  # type: ignore[attr-defined]
    elif IS_MAC:
        spawn_detached(["open", str(path)])
    else:
        spawn_detached(["xdg-open", str(path)])
