"""A button bar docked to the right of a scrcpy window.

It runs as its own process (`scrcpy-autolaunch _sidebar …`), one per mirror window:
on macOS, Tk and the tray icon both need the main thread, so they can't share a
process. The watcher starts it with the window, and it exits when scrcpy does.

- Key and gesture buttons go to the phone through one long-lived `adb shell`,
  so a press takes milliseconds rather than starting adb each time.
- Rotation and content size are changed by the tray app (it owns everything it
  changes on the phone and restores it later); the sidebar asks it through
  control.py.
- Windows: glued to the scrcpy window. It follows moves, resizes and
  minimizing, and never takes the keyboard focus away from the mirror.
  Elsewhere it's a small floating window (Wayland doesn't let apps read other
  windows' positions).
"""

from __future__ import annotations

import ctypes
import datetime
import logging
import os
import subprocess
import threading
from pathlib import Path

from scrcpy_autolaunch import control, theme
from scrcpy_autolaunch.osutil import IS_MAC, IS_WINDOWS, NO_WINDOW, find_process_window, open_path, open_terminal

log = logging.getLogger(__name__)

WIDTH = 52  # at 96 dpi
TRACK_MS = 30  # how often the docked bar follows the mirror window
ICON_FONTS = ("Segoe Fluent Icons", "Segoe MDL2 Assets")

# (key, Segoe icon glyph, text when that font isn't available, tooltip, phone command or None)
BUTTONS = [
    ("back", "\ue72b", "◁", "Back", "input keyevent 4"),
    ("home", "\ue80f", "○", "Home", "input keyevent 3"),
    ("recents", "\ue7c4", "□", "Recent apps", "input keyevent 187"),
    ("notifications", "\ue7e7", "Notif", "Open notifications", "cmd statusbar expand-notifications"),
    ("quick", "\ue713", "QS", "Open quick settings", "cmd statusbar expand-settings"),
    None,
    ("vol_up", "\ue995", "Vol+", "Volume up", "input keyevent 24"),
    ("vol_down", "\ue993", "Vol−", "Volume down", "input keyevent 25"),
    ("power", "\ue7e8", "Pwr", "Power button (screen on/off)", "input keyevent 26"),
    None,
    ("screenshot", "\ue722", "Shot", "Screenshot, saved to Pictures\\scrcpy-autolaunch (right-click: open the folder)", None),
    ("landscape", "\ue7ad", "Land", "Force landscape", None),
    ("shell", "\ue756", ">_", "Open an adb shell to the phone", None),
]
SCALE_GLYPH, SCALE_TEXT = "\ue740", "Size"


# ── phone side ───────────────────────────────────────────────────────────────


class PhoneShell:
    """One `adb shell` kept open; commands are written to its stdin."""

    def __init__(self, adb: str, serial: str):
        self.adb, self.serial = adb, serial
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def send(self, command: str) -> None:
        with self._lock:
            for attempt in (1, 2):
                if self._proc is None or self._proc.poll() is not None:
                    self._proc = subprocess.Popen(
                        [self.adb, "-s", self.serial, "shell"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        creationflags=NO_WINDOW,
                    )
                try:
                    self._proc.stdin.write(command + "\n")
                    self._proc.stdin.flush()
                    return
                except OSError:
                    self._proc = None
                    if attempt == 2:
                        raise

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()


def pictures_dir() -> Path:
    if IS_WINDOWS:
        try:
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

            # FOLDERID_Pictures {33E28130-4E1E-4676-835A-98395C3BC3BB}; follows OneDrive redirection.
            fid = GUID(0x33E28130, 0x4E1E, 0x4676, (ctypes.c_ubyte * 8)(0x83, 0x5A, 0x98, 0x39, 0x5C, 0x3B, 0xC3, 0xBB))
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(out)) == 0:
                path = Path(out.value)
                ctypes.windll.ole32.CoTaskMemFree(out)
                return path
        except Exception:
            pass
    elif not IS_MAC:
        try:
            out = subprocess.run(["xdg-user-dir", "PICTURES"], capture_output=True, text=True, timeout=5).stdout.strip()
            if out:
                return Path(out)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return Path.home() / "Pictures"


def screenshot_folder() -> Path:
    return pictures_dir() / "scrcpy-autolaunch"


def take_screenshot(adb: str, serial: str, name: str) -> Path:
    data = subprocess.run(
        [adb, "-s", serial, "exec-out", "screencap", "-p"],
        capture_output=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
        creationflags=NO_WINDOW,
    ).stdout
    if not data.startswith(b"\x89PNG"):
        raise OSError("the phone didn't return an image")
    folder = screenshot_folder()
    folder.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name) or "phone"
    path = folder / f"{safe}_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.png"
    path.write_bytes(data)
    return path


def process_alive(pid: int) -> bool:
    if IS_WINDOWS:
        SYNCHRONIZE, WAIT_TIMEOUT = 0x00100000, 0x102
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return False
        try:
            return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)  # signal 0 only checks; never used on Windows, where it would terminate
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


# ── docking (Windows) ────────────────────────────────────────────────────────


def dock_position(target: tuple[int, int, int, int], width: int, screen: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Where the bar goes for a mirror window at `target` (left, top, right, bottom).

    Right of the window; on its left if there's no room on the right of the screen
    (`screen` = virtual desktop left, top, right, bottom). Returns x, y, w, h.
    """
    left, top, right, bottom = target
    x = right
    if right + width > screen[2] and left - width >= screen[0]:
        x = left - width
    return x, top, width, max(bottom - top, 1)


class WindowsDock:
    GWL_EXSTYLE, GWLP_HWNDPARENT = -20, -8
    WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW = 0x08000000, 0x00000080
    DWMWA_EXTENDED_FRAME_BOUNDS = 9

    def __init__(self, root, pid: int, width: int):
        self.root, self.pid, self.width = root, pid, width
        self.target = None
        self.hidden = False
        self.last = None
        self.user32 = ctypes.windll.user32
        self.user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        self.user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        self.user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]

    def attach(self) -> bool:
        self.target = find_process_window(self.pid)
        if not self.target:
            return False
        own = self.user32.GetParent(self.root.winfo_id())
        # Owned by the mirror window: stays just above it, minimizes with it, no taskbar entry.
        self.user32.SetWindowLongPtrW(own, self.GWLP_HWNDPARENT, self.target)
        # Clicking a button doesn't take the keyboard focus away from the mirror.
        style = self.user32.GetWindowLongPtrW(own, self.GWL_EXSTYLE)
        self.user32.SetWindowLongPtrW(own, self.GWL_EXSTYLE, style | self.WS_EX_NOACTIVATE | self.WS_EX_TOOLWINDOW)
        return True

    def _bounds(self):
        from ctypes import wintypes

        rect = wintypes.RECT()
        # The visible frame, without Windows 10/11's invisible resize borders.
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(
            self.target, self.DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
        ):
            self.user32.GetWindowRect(self.target, ctypes.byref(rect))
        return rect.left, rect.top, rect.right, rect.bottom

    def _screen(self):
        g = self.user32.GetSystemMetrics
        x, y = g(76), g(77)  # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN
        return x, y, x + g(78), y + g(79)  # SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN

    def follow(self) -> bool:
        """Returns False once the mirror window is gone."""
        if not self.user32.IsWindow(self.target):
            return False
        if self.user32.IsIconic(self.target) or not self.user32.IsWindowVisible(self.target):
            if not self.hidden:
                self.root.withdraw()
                self.hidden = True
            return True
        x, y, w, h = dock_position(self._bounds(), self.width, self._screen())
        if (x, y, w, h) != self.last:
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.last = (x, y, w, h)
        if self.hidden:
            self.root.deiconify()
            self.hidden = False
        return True


# ── the window ───────────────────────────────────────────────────────────────


class Tooltip:
    def __init__(self, widget, text_fn):
        self.widget, self.text_fn = widget, text_fn
        self.tip = None
        self.job = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e=None):
        self._hide()
        self.job = self.widget.after(450, self._show)

    def _show(self):
        import tkinter as tk
        from tkinter import ttk

        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.attributes("-topmost", True)
        ttk.Label(self.tip, text=self.text_fn(), padding=(8, 4), relief="solid", borderwidth=1).pack()
        self.tip.update_idletasks()
        # Left of the bar, over the mirror: there's usually no room on the right.
        x = self.widget.winfo_rootx() - self.tip.winfo_width() - 6
        self.tip.geometry(f"+{x}+{self.widget.winfo_rooty() + 4}")

    def _hide(self, _e=None):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class Sidebar:
    def __init__(self, adb: str, serial: str, hw: str, pid: int, name: str, ctl: tuple[str, str] | None):
        import tkinter as tk
        from tkinter import font as tkfont
        from tkinter import ttk

        if IS_WINDOWS:
            try:  # crisp text, and coordinates in real pixels like the DWM bounds we read
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass

        self.adb, self.serial, self.hw, self.pid, self.name, self.ctl = adb, serial, hw, pid, name, ctl
        self.parent_pid = os.getppid()
        app = os.environ.get("SCRCPY_AUTOLAUNCH_APP_PID", "")
        self.app_pid = (int(app),) if app.isdigit() else ()
        self.shell = PhoneShell(adb, serial)
        self.root = root = tk.Tk()
        self.palette = theme.apply(root)
        root.title(f"{name} controls")
        self.width = round(WIDTH * root.winfo_fpixels("1i") / 96)

        families = set(tkfont.families(root))
        icon_font = next((f for f in ICON_FONTS if f in families), None)
        style = ttk.Style(root)
        style.configure("Icon.TButton", padding=4)
        if icon_font:
            style.configure("Icon.TButton", font=(icon_font, 13))
        # Sun Valley (Windows) has a proper toggle-button style; Tk's own themes use Toolbutton.
        toggle_style = "Toggle.TButton" if IS_WINDOWS else "Toolbutton"

        frame = ttk.Frame(root, padding=(4, 6))
        frame.pack(fill="both", expand=True)
        self.landscape = tk.BooleanVar(value=False)
        self.scale = tk.IntVar(value=100)

        for spec in BUTTONS:
            if spec is None:
                ttk.Separator(frame).pack(fill="x", pady=4)
                continue
            key, glyph, text, tip, command = spec
            label = glyph if icon_font else text
            if key == "landscape":
                w = ttk.Checkbutton(
                    frame, text=label, style=toggle_style, variable=self.landscape, command=self._toggle_landscape
                )
                if icon_font:
                    style.configure(toggle_style, font=(icon_font, 13))
            else:
                w = ttk.Button(frame, text=label, style="Icon.TButton", command=self._action(key, command))
            w.pack(fill="x", pady=1)
            Tooltip(w, lambda tip=tip: tip)
            if key == "screenshot":
                w.bind("<Button-3>", lambda _e: self._open_screenshots())

        ttk.Separator(frame).pack(fill="x", pady=4)
        size_label = ttk.Label(frame, text=SCALE_GLYPH if icon_font else SCALE_TEXT, anchor="center")
        if icon_font:
            size_label.configure(font=(icon_font, 12))
        size_label.pack(fill="x")
        self.scale_text = ttk.Label(frame, text="100%", anchor="center", font=("TkDefaultFont", 8))
        self.scale_text.pack(fill="x")
        slider = ttk.Scale(
            frame, orient="vertical", from_=100, to=50, command=self._slide, length=max(60, round(self.width * 2.4))
        )
        slider.pack(pady=(2, 4))
        slider.bind("<ButtonRelease-1>", lambda _e: self._apply_scale())
        self.slider = slider
        Tooltip(
            slider,
            lambda: "Content size: drag down to fit more on the screen.\nYour phone's own setting comes back when the window closes.",
        )

        self.status = ttk.Label(frame, text="", anchor="center", font=("TkDefaultFont", 8), wraplength=self.width - 8)
        self.status.pack(fill="x", side="bottom")

        self._load_state()
        self.dock = None
        if IS_WINDOWS:
            root.overrideredirect(True)
            root.geometry(f"{self.width}x400+-10000+-10000")  # off-screen until docked
            root.update_idletasks()
            self.dock = WindowsDock(root, pid, self.width)
            root.after(100, self._try_attach, 0)
        else:
            root.attributes("-topmost", True)
            root.geometry(f"+{root.winfo_screenwidth() - self.width - 40}+120")
        root.after(500, self._watch_scrcpy)

    # ── lifecycle ────────────────────────────────────────────────────────────

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.shell.close()

    def _try_attach(self, tries: int):
        if self.dock.attach():
            self._follow()
        elif tries < 150:  # scrcpy's window can take a few seconds to appear
            self.root.after(100, self._try_attach, tries + 1)
        else:  # couldn't find it: float instead
            self.dock = None
            self.root.overrideredirect(False)
            self.root.attributes("-topmost", True)
            self.root.geometry(f"+{self.root.winfo_screenwidth() - self.width - 40}+120")

    def _follow(self):
        if not self.dock.follow():
            self.root.destroy()
            return
        self.root.after(TRACK_MS, self._follow)

    def _watch_scrcpy(self):
        # Exit with the mirror window, and with the app (if it was killed it can't close us).
        # The parent check matters on Windows: the venv launcher sits in between, so the
        # app stopping the sidebar ends the launcher, not this process.
        if not all(process_alive(p) for p in (self.pid, self.parent_pid, *self.app_pid)):
            self.root.destroy()
            return
        self.root.after(500, self._watch_scrcpy)

    # ── actions ──────────────────────────────────────────────────────────────

    def _action(self, key: str, command: str | None):
        def run():
            if command:
                self._background(lambda: self.shell.send(command))
            elif key == "screenshot":
                self._screenshot()
            elif key == "shell":
                try:
                    open_terminal([self.adb, "-s", self.serial, "shell"])
                except OSError as exc:
                    self._say(str(exc), error=True)

        return run

    def _screenshot(self):
        self._say("…")

        def work():
            try:
                take_screenshot(self.adb, self.serial, self.name)
                self.root.after(0, self._say, "Saved")
            except Exception as exc:
                self.root.after(0, self._say, "Failed", True)
                self._report("warning", f"Screenshot failed: {exc}")

        threading.Thread(target=work, daemon=True).start()

    def _open_screenshots(self):
        folder = screenshot_folder()
        folder.mkdir(parents=True, exist_ok=True)
        open_path(folder)

    def _toggle_landscape(self):
        on = self.landscape.get()
        self._background(lambda: self._request({"cmd": "set_landscape", "on": on}))

    def _slide(self, value):
        self.scale_text.configure(text=f"{round(float(value) / 5) * 5}%")

    def _apply_scale(self):
        value = round(float(self.slider.get()) / 5) * 5
        self.slider.set(value)
        self._slide(value)
        if value == self._sent_scale:
            return
        self._sent_scale = value
        self._background(lambda: self._request({"cmd": "set_scale", "value": value}))

    def _load_state(self):
        self._sent_scale = 100
        reply = self._request({"cmd": "state"})
        if reply.get("ok"):
            self.landscape.set(bool(reply.get("force_landscape")))
            value = int(reply.get("content_scale", 100))
            self._sent_scale = value
            self.slider.set(value)
            self._slide(value)
        elif self.ctl is not None:
            self._say("Tray unreachable", error=True)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _request(self, msg: dict) -> dict:
        if self.ctl is None:
            return {"ok": False}
        try:
            return control.request(*self.ctl, msg)
        except Exception as exc:
            log.debug("Control request failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _report(self, level: str, message: str):
        self._request({"cmd": "log", "level": level, "message": f"[{self.serial}] {message}"})

    def _background(self, fn):
        def wrapped():
            try:
                fn()
            except Exception as exc:
                self.root.after(0, self._say, "Failed", True)
                self._report("warning", f"Sidebar action failed: {exc}")

        threading.Thread(target=wrapped, daemon=True).start()

    def _say(self, text: str, error: bool = False):
        self.status.configure(text=text, foreground=self.palette.error if error else self.palette.muted)
        if text:
            self.root.after(2500, lambda: self.status.configure(text=""))


def run_sidebar(adb: str, serial: str, hw: str, pid: int, name: str) -> int:
    ctl = control.parse_env(os.environ.get(control.ENV_VAR))
    try:
        Sidebar(adb, serial, hw, pid, name, ctl).run()
        return 0
    except Exception as exc:
        if ctl is not None:
            try:
                control.request(*ctl, {"cmd": "log", "level": "error", "message": f"[{serial}] sidebar crashed: {exc!r}"})
            except Exception:
                pass
        return 1
