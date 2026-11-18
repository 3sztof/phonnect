"""Start-at-login entries, one per OS, all per-user (no admin rights needed).

Windows: shortcut in the Startup folder (shell:startup)
macOS:   LaunchAgent in ~/Library/LaunchAgents
Linux:   XDG autostart entry in ~/.config/autostart
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from scrcpy_autolaunch.osutil import IS_MAC, IS_WINDOWS, gui_python

LABEL = "io.github.3sztof.scrcpy-autolaunch"
TRAY_EXE = "scrcpy-autolaunch-tray"


def tray_command() -> list[str]:
    """Command that starts the tray app without a console window."""
    name = TRAY_EXE + (".exe" if IS_WINDOWS else "")
    # The entry point next to our interpreter is the most stable path (the uv tool env).
    sibling = Path(sys.executable).parent / name
    if sibling.is_file():
        return [str(sibling)]
    found = shutil.which(TRAY_EXE)
    if found:
        return [found]
    return [gui_python(), "-m", "scrcpy_autolaunch", "tray"]


def entry_path() -> Path:
    home = Path.home()
    if IS_WINDOWS:
        appdata = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
        return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "scrcpy-autolaunch.lnk"
    if IS_MAC:
        return home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    return config / "autostart" / "scrcpy-autolaunch.desktop"


def is_enabled() -> bool:
    return entry_path().exists()


def enable(cmd: list[str] | None = None) -> Path:
    cmd = cmd or tray_command()
    path = entry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if IS_WINDOWS:
        _write_windows_shortcut(path, cmd)
    elif IS_MAC:
        path.write_bytes(macos_plist(cmd))
    else:
        path.write_text(linux_desktop_entry(cmd), encoding="utf-8")
    return path


def disable() -> bool:
    path = entry_path()
    if not path.exists():
        return False
    path.unlink()
    return True


# ── app menu entry (Start menu / Linux app launcher) ─────────────────────────


def menu_entry_path() -> Path | None:
    """Where the app-menu shortcut lives, or None where we don't create one (macOS)."""
    home = Path.home()
    if IS_WINDOWS:
        appdata = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
        return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "scrcpy-autolaunch.lnk"
    if IS_MAC:
        return None  # would need an .app bundle
    data = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    return data / "applications" / "scrcpy-autolaunch.desktop"


def add_menu_entry(cmd: list[str] | None = None) -> Path | None:
    path = menu_entry_path()
    if path is None:
        return None
    cmd = cmd or tray_command()
    path.parent.mkdir(parents=True, exist_ok=True)
    if IS_WINDOWS:
        _write_windows_shortcut(path, cmd)
    else:
        path.write_text(linux_desktop_entry(cmd, autostart=False), encoding="utf-8")
    return path


def remove_menu_entry() -> bool:
    path = menu_entry_path()
    if path is None or not path.exists():
        return False
    path.unlink()
    return True


def macos_plist(cmd: list[str]) -> bytes:
    return plistlib.dumps(
        {
            "Label": LABEL,
            "ProgramArguments": cmd,
            "RunAtLoad": True,
            "ProcessType": "Interactive",
            "LimitLoadToSessionType": "Aqua",  # GUI login session only
            # LaunchAgents get a bare PATH; include Homebrew so adb/scrcpy are found.
            "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
        }
    )


def _desktop_quote(arg: str) -> str:
    if arg and not any(c in arg for c in ' \t\n"\'\\$`'):
        return arg
    escaped = arg.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return f'"{escaped}"'


def linux_desktop_entry(cmd: list[str], autostart: bool = True) -> str:
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=scrcpy-autolaunch",
        "Comment=Open scrcpy when an Android device connects",
        "Exec=" + " ".join(_desktop_quote(a) for a in cmd),
        "Icon=smartphone",
        "Terminal=false",
    ]
    lines.append("X-GNOME-Autostart-enabled=true" if autostart else "Categories=Utility;")
    return "\n".join(lines + [""])


def _write_windows_shortcut(path: Path, cmd: list[str]) -> None:
    # Values go in through environment variables to avoid any quoting issues.
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:SAL_LNK);"
        "$s.TargetPath = $env:SAL_TARGET;"
        "$s.Arguments = $env:SAL_ARGS;"
        "$s.WorkingDirectory = $env:USERPROFILE;"
        "$s.Description = 'scrcpy-autolaunch tray';"
        "$s.Save()"
    )
    env = dict(
        os.environ,
        SAL_LNK=str(path),
        SAL_TARGET=cmd[0],
        SAL_ARGS=subprocess.list2cmdline(cmd[1:]),
    )
    subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
        env=env,
        check=True,
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
