"""OS detection and process helpers shared by the rest of the package."""

from __future__ import annotations

import os
import shlex
import shutil
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
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def find_process_window(pid: int) -> int | None:
    """Handle of the first visible top-level window of `pid` (Windows only)."""
    if not IS_WINDOWS:
        return None
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
    return found[0] if found else None


def focus_process_window(pid: int) -> bool:
    """Bring the visible top-level window of `pid` to the front (Windows only)."""
    hwnd = find_process_window(pid)
    if not hwnd:
        return False
    import ctypes

    SW_RESTORE = 9
    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return True


class _WindowDpiContext:
    """Read and set another app's window in that window's own coordinates (Windows).

    scrcpy's --window-x/-y/-width/-height use the coordinates scrcpy itself sees; with display
    scaling those differ from ours unless we switch this thread to the window's DPI mode.
    """

    def __init__(self, hwnd: int):
        self.hwnd, self.old = hwnd, None

    def __enter__(self):
        import ctypes

        user32 = ctypes.windll.user32
        try:
            user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
            user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
            user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            ctx = user32.GetWindowDpiAwarenessContext(self.hwnd)
            if ctx:
                self.old = user32.SetThreadDpiAwarenessContext(ctx)
        except AttributeError:  # Windows before 10 1607: one DPI mode for everything
            pass
        return self

    def __exit__(self, *exc):
        if self.old:
            import ctypes

            ctypes.windll.user32.SetThreadDpiAwarenessContext(self.old)


def window_client_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Content area of a normal (not minimized or maximized) window as x, y, width, height (Windows)."""
    if not IS_WINDOWS or not hwnd:
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    if not user32.IsWindow(hwnd) or user32.IsIconic(hwnd) or user32.IsZoomed(hwnd):
        return None
    with _WindowDpiContext(hwnd):
        rect, origin = wintypes.RECT(), wintypes.POINT(0, 0)
        if not user32.GetClientRect(hwnd, ctypes.byref(rect)) or not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
            return None
    if rect.right <= 0 or rect.bottom <= 0:
        return None
    return origin.x, origin.y, rect.right, rect.bottom


def set_window_client_size(hwnd: int, width: int, height: int) -> bool:
    """Resize a window so its content area is width x height, keeping its top-left corner (Windows)."""
    if not IS_WINDOWS or not hwnd:
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    with _WindowDpiContext(hwnd):
        outer, inner = wintypes.RECT(), wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(outer)) or not user32.GetClientRect(hwnd, ctypes.byref(inner)):
            return False
        extra_w = (outer.right - outer.left) - inner.right  # borders and title bar
        extra_h = (outer.bottom - outer.top) - inner.bottom
        SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE = 0x2, 0x4, 0x10
        return bool(
            user32.SetWindowPos(
                hwnd, 0, 0, 0, width + extra_w, height + extra_h, SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
            )
        )


def point_on_a_screen(x: int, y: int) -> bool:
    """Whether a point is on a connected monitor (Windows; elsewhere assumed yes)."""
    if not IS_WINDOWS:
        return True
    import ctypes
    from ctypes import wintypes

    MONITOR_DEFAULTTONULL = 0
    user32 = ctypes.windll.user32
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    return bool(user32.MonitorFromPoint(wintypes.POINT(x, y), MONITOR_DEFAULTTONULL))


# Linux terminals and how each one takes a command to run.
LINUX_TERMINALS = (
    ("x-terminal-emulator", ["-e"]),
    ("gnome-terminal", ["--"]),
    ("konsole", ["-e"]),
    ("xfce4-terminal", ["-x"]),
    ("kitty", []),
    ("alacritty", ["-e"]),
    ("wezterm", ["start", "--"]),
    ("foot", []),
    ("xterm", ["-e"]),
)


def linux_terminal_command(args: list[str], which=shutil.which, env=None) -> list[str] | None:
    env = os.environ if env is None else env
    preferred = env.get("TERMINAL")
    if preferred and which(preferred):
        return [preferred, "-e", *args]
    for name, flag in LINUX_TERMINALS:
        if which(name):
            return [name, *flag, *args]
    return None


def open_terminal(args: list[str]) -> None:
    """Run `args` in a new window of the OS's terminal app."""
    if IS_WINDOWS:
        # A new console goes to the user's default terminal app (Windows Terminal on Windows 11).
        subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE, close_fds=True)
    elif IS_MAC:
        command = shlex.join(args).replace("\\", "\\\\").replace('"', '\\"')
        spawn_detached(
            [
                "osascript",
                "-e",
                f'tell application "Terminal" to do script "{command}"',
                "-e",
                'tell application "Terminal" to activate',
            ]  # fmt: skip
        )
    else:
        cmd = linux_terminal_command(args)
        if cmd is None:
            raise OSError("No terminal app found. Set the TERMINAL environment variable to your terminal's command.")
        spawn_detached(cmd)


def open_path(path: Path) -> None:
    """Open a file or folder with the desktop's default application."""
    if IS_WINDOWS:
        os.startfile(path)  # type: ignore[attr-defined]
    elif IS_MAC:
        spawn_detached(["open", str(path)])
    else:
        spawn_detached(["xdg-open", str(path)])
