"""Tk windows: the Wi-Fi devices manager, and the pair / connect forms.

They run in a separate process (`scrcpy-autolaunch _dialog <kind>`): on macOS
both Tk and the tray icon need the main thread, so they can't share a process.
Every result is shown inside the window, so nothing depends on OS notifications.
"""

from __future__ import annotations

import queue
import threading
import time

from scrcpy_autolaunch.adb import Adb
from scrcpy_autolaunch.wireless import (
    KnownDevices,
    connect_verified,
    drop_offline,
    paired_guid,
    reconnect,
    split_address,
    status_of,
    wireless_serial_for,
)

PAIR_HELP = (
    "On the phone: Settings > System > Developer options > Wireless debugging >\n"
    "Pair device with pairing code.\n\n"
    "Enter the IP address & port and the 6-digit code shown in that popup.\n"
    "The phone and this computer must be on the same network."
)
CONNECT_HELP = (
    "On the phone: Settings > System > Developer options > Wireless debugging.\n\n"
    "Enter the IP address & port shown on that screen, NOT the one from the\n"
    "pairing popup. The port changes every time Wireless debugging is turned on."
)


def run_dialog(kind: str, adb: Adb, message: str = "") -> int:
    try:
        import tkinter as tk  # noqa: F401
    except ImportError:
        return 3  # caller shows the CLI alternative
    if kind == "devices":
        DevicesWindow(adb, message).run()
        return 0
    return _standalone_form(kind, adb)


class _Worker:
    """Runs blocking adb calls off the Tk thread and hands results back to it."""

    def __init__(self, root):
        self.root = root
        self.q: queue.Queue = queue.Queue()
        self.busy = False
        root.after(100, self._drain)

    def submit(self, fn, on_done, on_progress=None):
        if self.busy:
            return False
        self.busy = True

        def work():
            try:
                result = fn(lambda msg: self.q.put(("progress", on_progress, msg)))
            except Exception as exc:  # shown to the user, never silently dropped
                result = (False, f"Error: {exc}")
            self.q.put(("done", on_done, result))

        threading.Thread(target=work, daemon=True).start()
        return True

    def _drain(self):
        try:
            while True:
                kind, callback, value = self.q.get_nowait()
                if kind == "done":
                    self.busy = False
                if callback:
                    callback(value)
        except queue.Empty:
            pass
        self.root.after(100, self._drain)


def _form(parent, kind: str, adb: Adb, known: KnownDevices, on_finished):
    """Pair or connect form as a Toplevel. on_finished(ok, message)."""
    import tkinter as tk
    from tkinter import ttk

    win = tk.Toplevel(parent)
    win.title("Pair Android device" if kind == "pair" else "Connect to address")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    frame = ttk.Frame(win, padding=16)
    frame.grid()
    ttk.Label(frame, text=PAIR_HELP if kind == "pair" else CONNECT_HELP, justify="left").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )
    ttk.Label(frame, text="IP address:port").grid(row=1, column=0, sticky="w")
    address = ttk.Entry(frame, width=30)
    address.grid(row=1, column=1, sticky="we", pady=2)
    code = None
    if kind == "pair":
        ttk.Label(frame, text="Pairing code").grid(row=2, column=0, sticky="w")
        code = ttk.Entry(frame, width=30)
        code.grid(row=2, column=1, sticky="we", pady=2)
    status = ttk.Label(frame, text="", foreground="#555", wraplength=420, justify="left")
    status.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
    buttons = ttk.Frame(frame)
    buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))
    worker = _Worker(win)

    def work(progress):
        addr = address.get().strip()
        if not split_address(addr):
            return False, "Enter the address as IP:PORT, for example 192.168.1.20:37099."
        if kind == "pair":
            progress("Pairing…")
            ok, out = adb.pair(addr, code.get().strip() if code else "")
            if not ok:
                return False, f"Pairing failed:\n{out or 'no output from adb'}"
            hw = paired_guid(out)
            ip = split_address(addr)[0]
            if not hw:
                return True, "Paired. Now use Connect in the Wi-Fi devices window."
            known.remember(hw, ip=ip)
            progress("Paired. Connecting (this can take up to 30 seconds)…")
            time.sleep(2)  # give the phone a moment to advertise its connect port
            ok, result = reconnect(adb, known.get(hw), progress=progress)
            if ok:
                known.remember(hw, model=_model(adb, result), address=result)
                return True, f"Paired and connected ({result})."
            return True, f"Paired, but could not connect yet:\n{result}\n\nTry Connect to address with the port from the Wireless debugging screen."
        progress(f"Connecting to {addr}…")
        drop_offline(adb, split_address(addr)[0])
        ok, out = connect_verified(adb, addr)
        if ok:
            known.remember(adb.hardware_id(addr), model=_model(adb, addr), address=addr)
            return True, f"Connected ({addr})."
        return False, out

    def done(result):
        ok, msg = result
        status.config(text=msg, foreground="#1a7f37" if ok else "#b42318")
        go.state(["!disabled"])
        if ok:
            on_finished(True, msg)
            win.after(1200, win.destroy)

    def submit(_event=None):
        if worker.submit(work, done, lambda m: status.config(text=m, foreground="#555")):
            go.state(["disabled"])

    ttk.Button(buttons, text="Close", command=win.destroy).grid(row=0, column=0, padx=4)
    go = ttk.Button(buttons, text="Pair" if kind == "pair" else "Connect", command=submit)
    go.grid(row=0, column=1)
    win.bind("<Return>", submit)
    win.bind("<Escape>", lambda _e: win.destroy())
    address.focus_set()
    return win


def _model(adb: Adb, serial: str) -> str:
    try:
        return adb.run("-s", serial, "shell", "getprop", "ro.product.model", timeout=10).stdout.strip()
    except Exception:
        return ""


def _standalone_form(kind: str, adb: Adb) -> int:
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    result = {"code": 1}

    def finished(ok, _msg):
        result["code"] = 0 if ok else 1

    win = _form(root, kind, adb, KnownDevices(), finished)
    win.bind("<Destroy>", lambda e: root.destroy() if e.widget is win else None)
    root.mainloop()
    return result["code"]


class DevicesWindow:
    def __init__(self, adb: Adb, message: str = ""):
        import tkinter as tk
        from tkinter import ttk

        self.adb = adb
        self.known = KnownDevices()
        self.root = tk.Tk()
        self.root.title("Wi-Fi devices - scrcpy-autolaunch")
        self.root.minsize(560, 300)
        self.worker = _Worker(self.root)

        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="Phones paired with this computer, or seen before. Select one and click Connect.\n"
            "Wireless debugging must be on on the phone (Developer options).",
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        columns = ("phone", "status", "address", "seen")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=7, selectmode="browse")
        for col, title, width in (
            ("phone", "Phone", 160),
            ("status", "Status", 110),
            ("address", "Last address", 150),
            ("seen", "Last seen", 120),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _e: self.connect())

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(8, 0))
        self.buttons = [
            ttk.Button(buttons, text="Connect", command=self.connect),
            ttk.Button(buttons, text="Disconnect", command=self.disconnect),
            ttk.Button(buttons, text="Pair new device…", command=lambda: self.form("pair")),
            ttk.Button(buttons, text="Connect to address…", command=lambda: self.form("connect")),
            ttk.Button(buttons, text="Refresh", command=self.refresh),
        ]
        for i, b in enumerate(self.buttons):
            b.grid(row=0, column=i, padx=(0, 6))
        ttk.Button(buttons, text="Close", command=self.root.destroy).grid(row=0, column=len(self.buttons))

        self.status = ttk.Label(frame, text=message, wraplength=640, justify="left")
        self.status.pack(anchor="w", pady=(10, 0))
        self.root.bind("<Escape>", lambda _e: self.root.destroy())
        self.root.bind("<F5>", lambda _e: self.refresh())
        self.refresh()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(500, lambda: self.root.attributes("-topmost", False))

    def run(self):
        self.root.mainloop()

    def say(self, text: str, ok: bool | None = None):
        color = {True: "#1a7f37", False: "#b42318", None: "#555"}[ok]
        self.status.config(text=text, foreground=color)

    def refresh(self):
        def work(_progress):
            devices = self.adb.devices()
            rows = []
            for d in self.known.all():
                seen = time.strftime("%Y-%m-%d %H:%M", time.localtime(d.last_seen)) if d.last_seen else "never"
                rows.append((d.hw_id, (d.label, status_of(d, devices), d.address or "-", seen)))
            return True, rows

        def done(result):
            ok, rows = result
            if not ok:
                self.say(rows, False)
                return
            selected = self.tree.selection()
            self.tree.delete(*self.tree.get_children())
            for hw, values in rows:
                self.tree.insert("", "end", iid=hw, values=values)
            if selected and self.tree.exists(selected[0]):
                self.tree.selection_set(selected[0])
            elif rows:
                self.tree.selection_set(rows[0][0])
            if not rows:
                self.say("No phones yet. Click 'Pair new device…' to pair one.")

        self.worker.submit(work, done)

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            self.say("Select a phone first.", False)
            return None
        return self.known.get(sel[0])

    def connect(self):
        device = self._selected()
        if device is None:
            return

        def work(progress):
            ok, result = reconnect(self.adb, device, progress=progress)
            if ok:
                self.known.remember(device.hw_id, model=_model(self.adb, result) or device.model, address=result)
                return True, f"Connected to {device.label} at {result}."
            return False, (
                f"Could not connect to {device.label}.\n{result}\n\n"
                "Check that Wireless debugging is on and the phone is on the same network. "
                "If the phone shows a different IP address & port, use 'Connect to address…'."
            )

        self._run(work, f"Connecting to {device.label}…")

    def disconnect(self):
        device = self._selected()
        if device is None:
            return

        def work(_progress):
            serial = wireless_serial_for(device, self.adb.devices())
            if serial is None:
                return False, f"{device.label} is not connected over Wi-Fi."
            self.adb.disconnect(serial)
            return True, f"Disconnected {device.label}."

        self._run(work, "Disconnecting…")

    def _run(self, work, start_text):
        def done(result):
            ok, msg = result
            self.say(msg, ok)
            for b in self.buttons:
                b.state(["!disabled"])
            self.refresh()

        if self.worker.submit(work, done, lambda m: self.say(m)):
            self.say(start_text)
            for b in self.buttons:
                b.state(["disabled"])

    def form(self, kind):
        _form(self.root, kind, self.adb, self.known, lambda ok, msg: (self.say(msg, ok), self.refresh()))
