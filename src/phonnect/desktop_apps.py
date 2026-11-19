"""Apps panel next to the desktop-mode window: a workaround, until the desktop's own taskbar works.

On current Pixels (Android 16/17) the desktop's taskbar can't open apps on scrcpy's virtual
screen (scrcpy #6699, #7048; fix proposed in #7055). Starting an app with
`am start --display N` works, so this panel lists the phone's apps and opens them there.
Apps opened this way have no title bars, so the panel also switches between them and closes
them. Runs as its own process (`phonnect _desktop_apps`), like the sidebar.
"""

from __future__ import annotations

import logging
import os
import queue
import re
import subprocess
import threading
from dataclasses import dataclass

from phonnect import control, theme
from phonnect.osutil import IS_MAC, IS_WINDOWS, NO_WINDOW

log = logging.getLogger(__name__)

WIDTH = 250  # at 96 dpi
REFRESH_MS = 3000
LAUNCHER = ("-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER")
LABEL_RE = re.compile(r"^\s*[*-]\s+(.+?)\s{2,}([A-Za-z0-9_.]+)\s*$")
TASK_RE = re.compile(r"Task\{\w+ #(\d+) type=standard A=\d+:([\w.]+).*?mode=(\w+)")
WINDOWING = {"fullscreen": "1", "window": "5"}  # ActivityManager windowing modes


@dataclass(frozen=True)
class App:
    label: str
    package: str
    component: str  # package/.Activity, the app's launcher entry


def parse_launcher_activities(text: str) -> dict[str, str]:
    """`cmd package query-activities --brief ...` -> {package: component}."""
    found: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if "/" in line and " " not in line:
            package = line.split("/", 1)[0]
            found.setdefault(package, line)
    return found


def parse_app_labels(text: str) -> dict[str, str]:
    """`scrcpy --list-apps` -> {package: label}."""
    labels = {}
    for line in text.splitlines():
        m = LABEL_RE.match(line)
        if m:
            labels[m.group(2)] = m.group(1).strip()
    return labels


def parse_display_tasks(dumpsys: str, display_id: int) -> list[tuple[int, str, str]]:
    """Apps open on one display, from `dumpsys activity activities`: [(task id, package, mode)]."""
    lines = dumpsys.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(f"Display #{display_id} ")), None)
    if start is None:
        return []
    tasks, seen = [], set()
    for line in lines[start + 1 :]:
        if line.startswith("Display #"):
            break
        m = TASK_RE.search(line)
        if m and int(m.group(1)) not in seen:
            seen.add(int(m.group(1)))
            tasks.append((int(m.group(1)), m.group(2), m.group(3)))
    return tasks


def apps_from(components: dict[str, str], labels: dict[str, str]) -> list[App]:
    apps = [App(labels.get(p) or p.rsplit(".", 1)[-1], p, c) for p, c in components.items()]
    return sorted(apps, key=lambda a: a.label.lower())


class Phone:
    """adb calls for one phone and one display."""

    def __init__(self, adb: str, serial: str, display_id: int, scrcpy: str | None = None):
        self.adb, self.serial, self.display_id, self.scrcpy = adb, serial, display_id, scrcpy

    def _run(self, *args: str, timeout: float = 15) -> str:
        r = subprocess.run(
            [self.adb, "-s", self.serial, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            creationflags=NO_WINDOW,
        )
        return r.stdout + r.stderr

    def launcher_components(self) -> dict[str, str]:
        return parse_launcher_activities(self._run("shell", "cmd", "package", "query-activities", "--brief", *LAUNCHER))

    def labels(self) -> dict[str, str]:
        """App names; takes a few seconds (scrcpy reads them on the phone)."""
        if not self.scrcpy:
            return {}
        try:
            r = subprocess.run(
                [self.scrcpy, "-s", self.serial, "--list-apps"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=30,
                env=dict(os.environ, ADB=self.adb),
                creationflags=NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {}
        return parse_app_labels(r.stdout + r.stderr)

    def open(self, app: App, mode: str = "fullscreen") -> str:
        out = self._run(
            "shell", "am", "start", "--display", str(self.display_id),
            "--windowingMode", WINDOWING.get(mode, "1"), *LAUNCHER, "-n", app.component,
        )  # fmt: skip
        return "" if "Error" not in out else out.strip().splitlines()[-1]

    def tasks(self) -> list[tuple[int, str, str]]:
        return parse_display_tasks(self._run("shell", "dumpsys", "activity", "activities", timeout=20), self.display_id)

    def close(self, task_id: int) -> None:
        self._run("shell", "am", "stack", "remove", str(task_id))

    def home(self) -> None:
        self._run("shell", "input", "-d", str(self.display_id), "keyevent", "3")


class AppsPanel:
    def __init__(self, phone: Phone, pid: int, name: str, ctl):
        import tkinter as tk
        from tkinter import ttk

        if IS_WINDOWS:
            import ctypes

            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass
        self.phone, self.pid, self.ctl = phone, pid, ctl
        self.apps: list[App] = []
        self.shown: list[App] = []
        self.running: list[tuple[int, str, str]] = []
        self.q: queue.Queue = queue.Queue()
        self.root = root = tk.Tk()
        if IS_MAC:
            from phonnect.tray import hide_dock_icon

            hide_dock_icon()
        self.palette = theme.apply(root)
        root.title(f"{name} desktop apps")
        self.width = WIDTH if IS_MAC else round(WIDTH * root.winfo_fpixels("1i") / 96)

        frame = ttk.Frame(root, padding=8)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Apps", font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Workaround: the desktop's own taskbar can't open apps yet. Open them here.",
            foreground=self.palette.muted,
            wraplength=self.width - 24,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self._filter())
        entry = ttk.Entry(frame, textvariable=self.search)
        entry.pack(fill="x")
        entry.bind("<Return>", lambda _e: self._open_selected())
        entry.bind("<Down>", lambda _e: (self.listbox.focus_set(), self.listbox.selection_set(0)))

        self.listbox = tk.Listbox(frame, height=14, activestyle="none", exportselection=False, borderwidth=0)
        self.listbox.pack(fill="both", expand=True, pady=(4, 4))
        self.listbox.bind("<Double-Button-1>", lambda _e: self._open_selected())
        self.listbox.bind("<Return>", lambda _e: self._open_selected())

        self.windowed = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Open in a window (no title bar)", variable=self.windowed).pack(anchor="w")
        ttk.Button(frame, text="Open", command=self._open_selected).pack(fill="x", pady=(4, 8))

        ttk.Separator(frame).pack(fill="x", pady=4)
        ttk.Label(frame, text="Open on the desktop", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.running_box = tk.Listbox(frame, height=6, activestyle="none", exportselection=False, borderwidth=0)
        self.running_box.pack(fill="x", pady=(4, 4))
        self.running_box.bind("<Double-Button-1>", lambda _e: self._switch())
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Switch to", command=self._switch).pack(side="left", expand=True, fill="x")
        ttk.Button(buttons, text="Close", command=self._close).pack(side="left", expand=True, fill="x", padx=4)
        ttk.Button(buttons, text="Desktop", command=lambda: self._work(self.phone.home)).pack(
            side="left", expand=True, fill="x"
        )
        self.status = ttk.Label(frame, text="Loading apps…", foreground=self.palette.muted, wraplength=self.width - 24)
        self.status.pack(anchor="w", pady=(6, 0))

        self._colour_lists()
        self.dock = None
        root.update_idletasks()
        self.width = max(self.width, frame.winfo_reqwidth())
        if IS_WINDOWS or IS_MAC:
            from phonnect.sidebar import MacDock, WindowsDock

            root.overrideredirect(True)
            root.geometry(f"{self.width}x500+-10000+-10000")
            root.update_idletasks()
            self.dock = WindowsDock(root, pid, self.width) if IS_WINDOWS else MacDock(root, pid, self.width)
            root.after(100, self._try_attach, 0)
        else:
            root.attributes("-topmost", True)
        root.after(100, self._drain)
        root.after(1000, self._watch_desktop)
        self._work(self._load_apps)
        self._refresh_running()

    # ── lifecycle ────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()

    def _try_attach(self, tries: int):
        if self.dock.attach():
            self._follow()
        elif tries < 150:
            self.root.after(100, self._try_attach, tries + 1)
        else:
            self.dock = None
            self.root.overrideredirect(False)

    def _follow(self):
        if not self.dock.follow():
            self.root.destroy()
            return
        self.root.after(50, self._follow)

    def _watch_desktop(self):
        from phonnect.sidebar import process_alive

        if not process_alive(self.pid):
            self.root.destroy()
            return
        self.root.after(1000, self._watch_desktop)

    def _colour_lists(self):
        # Classic Tk listboxes don't follow the ttk theme: match it by hand.
        dark = theme.is_dark()
        colours = dict(
            background="#2b2b2b" if dark else "#ffffff",
            foreground="#e8e8e8" if dark else "#1f1f1f",
            selectbackground="#0a64a4" if dark else "#cce4f7",
            selectforeground="#ffffff" if dark else "#000000",
            highlightthickness=0,
        )
        for box in (self.listbox, self.running_box):
            try:
                box.configure(**colours)
            except Exception:
                pass

    # ── work off the Tk thread ───────────────────────────────────────────────

    def _work(self, fn, done=None):
        def run():
            try:
                result = fn()
            except Exception as exc:
                result = exc
            self.q.put((done, result))

        threading.Thread(target=run, daemon=True).start()

    def _drain(self):
        try:
            while True:
                done, result = self.q.get_nowait()
                if isinstance(result, Exception):
                    self._say(f"Failed: {result}", error=True)
                    self._log("warning", f"desktop apps: {result!r}")
                elif done is not None:
                    done(result)
        except queue.Empty:
            pass
        self.root.after(100, self._drain)

    # ── apps ─────────────────────────────────────────────────────────────────

    def _load_apps(self):
        components = self.phone.launcher_components()
        self.q.put((self._set_apps, apps_from(components, {})))  # package names at once…
        return apps_from(components, self.phone.labels())  # …then the real names

    def _set_apps(self, apps):
        self.apps = apps
        self._filter()
        self._say(f"{len(apps)} apps" if apps else "No apps found", error=not apps)

    def _filter(self):
        term = self.search.get().strip().lower()
        self.shown = [a for a in self.apps if term in a.label.lower() or term in a.package.lower()]
        self.listbox.delete(0, "end")
        for a in self.shown:
            self.listbox.insert("end", a.label)

    def _open_selected(self):
        sel = self.listbox.curselection()
        if not sel and len(self.shown) == 1:
            sel = (0,)
        if not sel:
            self._say("Select an app first.", error=True)
            return
        app = self.shown[sel[0]]
        mode = "window" if self.windowed.get() else "fullscreen"
        self._say(f"Opening {app.label}…")
        self._work(lambda: self.phone.open(app, mode), lambda err: self._opened(app, err))

    def _opened(self, app: App, error: str):
        self._say(f"Couldn't open {app.label}: {error}" if error else f"Opened {app.label}", error=bool(error))
        self.root.after(800, self._refresh_running)

    # ── apps open on the desktop ─────────────────────────────────────────────

    def _refresh_running(self):
        self._work(self.phone.tasks, self._set_running)

    def _set_running(self, tasks):
        if tasks != self.running:
            labels = {a.package: a.label for a in self.apps}
            selected = self.running_box.curselection()
            keep = self.running[selected[0]][0] if selected and selected[0] < len(self.running) else None
            self.running = tasks
            self.running_box.delete(0, "end")
            for i, (task_id, package, mode) in enumerate(tasks):
                suffix = "" if mode == "fullscreen" else "  (window)"
                self.running_box.insert("end", labels.get(package, package) + suffix)
                if task_id == keep:
                    self.running_box.selection_set(i)
        self.root.after(REFRESH_MS, self._refresh_running)

    def _selected_task(self):
        sel = self.running_box.curselection()
        if not sel or sel[0] >= len(self.running):
            self._say("Select an open app first.", error=True)
            return None
        return self.running[sel[0]]

    def _switch(self):
        task = self._selected_task()
        if task is None:
            return
        app = next((a for a in self.apps if a.package == task[1]), None)
        if app is None:
            return
        mode = "window" if task[2] == "freeform" else "fullscreen"
        self._work(lambda: self.phone.open(app, mode), lambda err: self._say(err, error=True) if err else None)

    def _close(self):
        task = self._selected_task()
        if task is None:
            return
        self._work(lambda: self.phone.close(task[0]), lambda _r: self.root.after(500, self._refresh_running))

    # ── helpers ──────────────────────────────────────────────────────────────

    def _say(self, text: str, error: bool = False):
        self.status.configure(text=text, foreground=self.palette.error if error else self.palette.muted)

    def _log(self, level: str, message: str):
        if self.ctl is None:
            return
        try:
            control.request(*self.ctl, {"cmd": "log", "level": level, "message": message})
        except Exception:
            pass


def run_desktop_apps(adb: str, serial: str, display_id: int, pid: int, name: str, scrcpy: str | None) -> int:
    ctl = control.parse_env(os.environ.get(control.ENV_VAR))
    try:
        AppsPanel(Phone(adb, serial, display_id, scrcpy), pid, name, ctl).run()
        return 0
    except Exception as exc:
        if ctl is not None:
            try:
                control.request(*ctl, {"cmd": "log", "level": "error", "message": f"desktop apps crashed: {exc!r}"})
            except Exception:
                pass
        return 1
