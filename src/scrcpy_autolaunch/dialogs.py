"""Small Tk dialogs for wireless pairing and connecting.

They run in a separate process (`scrcpy-autolaunch _dialog pair|connect`):
on macOS both Tk and the tray icon need the main thread, so they can't share one.
"""

from __future__ import annotations

from scrcpy_autolaunch.adb import Adb

PAIR_HELP = (
    "On the phone: Settings > Developer options > Wireless debugging >\n"
    "Pair device with pairing code.\n\n"
    "Enter the IP address & port and the 6-digit code shown there.\n"
    "The phone and this computer must be on the same network."
)
CONNECT_HELP = (
    "On the phone: Settings > Developer options > Wireless debugging.\n\n"
    "Enter the IP address & port shown on that screen (not the pairing port)."
)


def run_dialog(kind: str, adb: Adb) -> int:
    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
    except ImportError:
        return 3  # caller shows the CLI alternative

    root = tk.Tk()
    root.title("Pair Android device" if kind == "pair" else "Connect Android device")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    frame = ttk.Frame(root, padding=16)
    frame.grid()

    ttk.Label(frame, text=PAIR_HELP if kind == "pair" else CONNECT_HELP, justify="left").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )
    ttk.Label(frame, text="IP address:port").grid(row=1, column=0, sticky="w")
    address = ttk.Entry(frame, width=28)
    address.grid(row=1, column=1, sticky="we", pady=2)
    code = None
    if kind == "pair":
        ttk.Label(frame, text="Pairing code").grid(row=2, column=0, sticky="w")
        code = ttk.Entry(frame, width=28)
        code.grid(row=2, column=1, sticky="we", pady=2)
    address.focus_set()

    result = {"code": 1}

    def submit(_event=None):
        addr = address.get().strip()
        if not addr:
            return
        root.config(cursor="watch")
        root.update()
        if kind == "pair":
            ok, out = adb.pair(addr, code.get().strip() if code else "")
            msg = (
                "Paired. The phone usually connects on its own within a few seconds.\n"
                "If it doesn't, use 'Connect to address…' from the tray menu."
                if ok
                else f"Pairing failed:\n\n{out or 'no output from adb'}"
            )
        else:
            ok, out = adb.connect(addr)
            msg = out or ("Connected." if ok else "Connection failed.")
        root.config(cursor="")
        (messagebox.showinfo if ok else messagebox.showerror)(root.title(), msg, parent=root)
        if ok:
            result["code"] = 0
            root.destroy()

    buttons = ttk.Frame(frame)
    buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
    ttk.Button(buttons, text="Cancel", command=root.destroy).grid(row=0, column=0, padx=4)
    ttk.Button(buttons, text="Pair" if kind == "pair" else "Connect", command=submit).grid(row=0, column=1)
    root.bind("<Return>", submit)
    root.bind("<Escape>", lambda _e: root.destroy())
    root.mainloop()
    return result["code"]
