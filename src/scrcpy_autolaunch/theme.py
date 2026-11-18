"""Make the Tk windows and the tray menu match the OS look, in light or dark mode.

Windows: Sun Valley ttk theme (Windows 11 Fluent style), dark title bar via DWM,
         dark tray menus via uxtheme
macOS:   nothing to do: Tk's native Aqua theme already follows light/dark mode
Linux:   Tk's built-in "clam" theme recoloured with GNOME's Adwaita palette
"""

from __future__ import annotations

import ctypes
import logging
from dataclasses import dataclass

from scrcpy_autolaunch.osutil import IS_LINUX, IS_WINDOWS

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Palette:
    """Text colours for status messages, readable on the window background."""

    muted: str
    ok: str
    error: str


LIGHT = Palette(muted="#5f6368", ok="#1a7f37", error="#b42318")
DARK = Palette(muted="#a8adb4", ok="#4ade80", error="#f87171")

# GNOME Adwaita (libadwaita) colours.
ADWAITA = {
    False: dict(bg="#fafafa", fg="#2e3436", field="#ffffff", border="#d0d0d0", button="#ececec", hover="#e0e0e0"),
    True: dict(bg="#242424", fg="#ffffff", field="#1e1e1e", border="#3d3d3d", button="#353535", hover="#424242"),
}
ADWAITA_ACCENT = "#3584e4"


def is_dark() -> bool:
    """Whether apps should use dark mode (Windows: the 'app mode' setting)."""
    try:
        import darkdetect

        return bool(darkdetect.isDark())
    except Exception:
        return False


def apply(root) -> Palette:
    """Theme a Tk root window. Call before the window is shown. Never raises."""
    dark = is_dark()
    try:
        if IS_WINDOWS:
            import sv_ttk

            sv_ttk.set_theme("dark" if dark else "light", root)
            root.after(0, title_bar, root, dark)  # the native window exists once Tk maps it
        elif IS_LINUX:
            _adwaita(root, dark)
        # macOS: Aqua handles it.
    except Exception:
        log.debug("Theming failed; using the default Tk look", exc_info=True)
    return DARK if dark else LIGHT


def title_bar(window, dark: bool | None = None) -> None:
    """Windows 10 20H1+/11: dark or light title bar for a Tk window (no-op elsewhere)."""
    if not IS_WINDOWS:
        return
    if dark is None:
        dark = is_dark()
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1 if dark else 0)
        # DWMWA_USE_IMMERSIVE_DARK_MODE is 20; Windows 10 builds before 20H1 used 19.
        for attribute in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:
        log.debug("Could not set the title bar colour", exc_info=True)


def _adwaita(root, dark: bool) -> None:
    from tkinter import ttk

    c = ADWAITA[dark]
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".",
        background=c["bg"],
        foreground=c["fg"],
        fieldbackground=c["field"],
        bordercolor=c["border"],
        lightcolor=c["bg"],
        darkcolor=c["border"],
        troughcolor=c["border"],
        selectbackground=ADWAITA_ACCENT,
        selectforeground="#ffffff",
        insertcolor=c["fg"],
    )
    style.configure("TButton", background=c["button"], padding=(12, 5), relief="flat")
    style.map("TButton", background=[("pressed", c["border"]), ("active", c["hover"])])
    style.configure("TEntry", padding=4)
    style.configure("Treeview", background=c["field"], fieldbackground=c["field"], foreground=c["fg"], rowheight=26)
    style.configure("Treeview.Heading", background=c["button"], foreground=c["fg"], relief="flat")
    style.map("Treeview", background=[("selected", ADWAITA_ACCENT)], foreground=[("selected", "#ffffff")])
    root.configure(background=c["bg"])
    root.option_add("*Toplevel.background", c["bg"])


# ── tray menu (Windows) ──────────────────────────────────────────────────────


def system_is_light() -> bool:
    """Windows: the 'system' (taskbar, tray) mode, which can differ from the app mode."""
    if not IS_WINDOWS:
        return True
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        ) as key:
            return winreg.QueryValueEx(key, "SystemUsesLightTheme")[0] == 1
    except OSError:
        return True


_PREFERRED_APP_MODE = {"force_dark": 2, "force_light": 3}


def match_tray_menu_theme() -> None:
    """Draw this process's popup menus dark or light like Windows' own tray menus.

    Classic Win32 menus are always light unless the app opts in through two
    undocumented but long-stable uxtheme exports (Windows 10 1903+), also used by
    e.g. Notepad++ and Windows Terminal. Best effort: does nothing if unavailable.
    """
    if not IS_WINDOWS:
        return
    try:
        uxtheme = ctypes.WinDLL("uxtheme")
        set_preferred_app_mode = uxtheme[135]
        set_preferred_app_mode.argtypes = [ctypes.c_int]
        set_preferred_app_mode(_PREFERRED_APP_MODE["force_light" if system_is_light() else "force_dark"])
        uxtheme[136]()  # FlushMenuThemes
    except Exception:
        log.debug("Could not set the tray menu theme", exc_info=True)
