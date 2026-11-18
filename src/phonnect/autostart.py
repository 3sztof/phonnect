"""Start-at-login entries, one per OS, all per-user (no admin rights needed).

Windows: shortcut in the Startup folder (shell:startup)
macOS:   LaunchAgent in ~/Library/LaunchAgents
Linux:   XDG autostart entry in ~/.config/autostart
"""

from __future__ import annotations

import os
import plistlib
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from phonnect.osutil import IS_MAC, IS_WINDOWS, gui_python

LABEL = "io.github.3sztof.phonnect"
TRAY_EXE = "phonnect-tray"


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
    return [gui_python(), "-m", "phonnect", "tray"]


def entry_path() -> Path:
    home = Path.home()
    if IS_WINDOWS:
        appdata = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
        return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Phonnect.lnk"
    if IS_MAC:
        return home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    return config / "autostart" / "phonnect.desktop"


def is_enabled() -> bool:
    return entry_path().exists()


def enable(cmd: list[str] | None = None) -> Path:
    cmd = cmd or tray_command()
    path = entry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if IS_WINDOWS:
        _write_windows_shortcut(path, cmd, _icon_file(".ico"))
    elif IS_MAC:
        path.write_bytes(macos_plist(cmd))
    else:
        path.write_text(linux_desktop_entry(cmd, icon=_icon_file(".png")), encoding="utf-8")
    return path


def _icon_file(suffix: str) -> str:
    """Path of the generated app icon, or '' if it can't be written (the shortcut still works)."""
    try:
        from phonnect.icons import ensure_icon_files

        ico, png = ensure_icon_files()
        return str(ico if suffix == ".ico" else png)
    except Exception:
        return ""


def disable() -> bool:
    path = entry_path()
    if not path.exists():
        return False
    path.unlink()
    return True


def legacy_entries() -> list[Path]:
    """Start-at-login and menu entries left by the app's old name (scrcpy-autolaunch)."""
    home = Path.home()
    if IS_WINDOWS:
        programs = (
            Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
        )
        candidates = [programs / "Startup" / "scrcpy-autolaunch.lnk", programs / "scrcpy-autolaunch.lnk"]
    elif IS_MAC:
        candidates = [home / "Library" / "LaunchAgents" / "io.github.3sztof.scrcpy-autolaunch.plist"]
    else:
        config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        data = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
        candidates = [
            config / "autostart" / "scrcpy-autolaunch.desktop",
            data / "applications" / "scrcpy-autolaunch.desktop",
        ]
    return [p for p in candidates if p.exists()]


def remove_legacy_entries() -> list[Path]:
    removed = []
    for p in legacy_entries():
        try:
            p.unlink()
            removed.append(p)
        except OSError:
            pass
    return removed


# ── app menu entry (Start menu / Linux app launcher) ─────────────────────────


def menu_entry_path() -> Path:
    """Where the app-menu entry lives: Start menu shortcut, app bundle (macOS) or launcher entry (Linux)."""
    home = Path.home()
    if IS_WINDOWS:
        appdata = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
        return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Phonnect.lnk"
    if IS_MAC:
        # ~/Applications is per-user, and Spotlight and Launchpad list what's in it.
        return home / "Applications" / "Phonnect.app"
    data = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    return data / "applications" / "phonnect.desktop"


def add_menu_entry(cmd: list[str] | None = None) -> Path:
    path = menu_entry_path()
    cmd = cmd or tray_command()
    path.parent.mkdir(parents=True, exist_ok=True)
    if IS_WINDOWS:
        _write_windows_shortcut(path, cmd, _icon_file(".ico"))
    elif IS_MAC:
        write_mac_app(path, cmd)
    else:
        path.write_text(linux_desktop_entry(cmd, autostart=False, icon=_icon_file(".png")), encoding="utf-8")
    return path


def remove_menu_entry() -> bool:
    path = menu_entry_path()
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def refresh_entries(version: str) -> list[Path]:
    """After an update, rewrite the entries that exist, so they point at the new install.

    Also gives entries made by older versions their current names (phonnect.lnk -> Phonnect.lnk).
    Runs once per version; returns the entries rewritten.
    """
    from phonnect import paths

    marker = paths.state_dir() / "entries-version"
    try:
        if marker.read_text(encoding="utf-8").strip() == version:
            return []
    except OSError:
        pass
    done = []
    if is_enabled():
        done.append(enable())
    if menu_entry_path().exists():
        done.append(add_menu_entry())
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(version, encoding="utf-8")
    return done


def mac_info_plist(version: str = "") -> bytes:
    return plistlib.dumps(
        {
            "CFBundleName": "Phonnect",
            "CFBundleDisplayName": "Phonnect",
            "CFBundleIdentifier": LABEL,
            "CFBundleExecutable": "Phonnect",
            "CFBundleIconFile": "Phonnect.icns",
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": version or "0",
            "LSUIElement": True,  # menu bar app: no Dock icon
            "NSHighResolutionCapable": True,
        }
    )


def write_mac_app(path: Path, cmd: list[str]) -> None:
    """A minimal app bundle that starts the tray, so Phonnect shows up in Spotlight, Launchpad and Finder."""
    from phonnect import __version__

    contents = path / "Contents"
    (contents / "MacOS").mkdir(parents=True, exist_ok=True)
    (contents / "Resources").mkdir(parents=True, exist_ok=True)
    (contents / "Info.plist").write_bytes(mac_info_plist(__version__))
    launcher = contents / "MacOS" / "Phonnect"
    launcher.write_text("#!/bin/sh\nexec " + " ".join(shlex.quote(a) for a in cmd) + "\n", encoding="utf-8")
    launcher.chmod(0o755)
    try:
        from phonnect.icons import app_icon

        app_icon(1024).save(contents / "Resources" / "Phonnect.icns")
    except Exception:
        pass  # the bundle still works, with a generic icon


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
    if arg and not any(c in arg for c in " \t\n\"'\\$`"):
        return arg
    escaped = arg.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return f'"{escaped}"'


def linux_desktop_entry(cmd: list[str], autostart: bool = True, icon: str = "") -> str:
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=Phonnect",
        "Comment=Your phone on your desktop, the moment it connects",
        "Exec=" + " ".join(_desktop_quote(a) for a in cmd),
        f"Icon={icon or 'smartphone'}",
        "Terminal=false",
    ]
    lines.append("X-GNOME-Autostart-enabled=true" if autostart else "Categories=Utility;")
    return "\n".join(lines + [""])


def _write_windows_shortcut(path: Path, cmd: list[str], icon: str = "") -> None:
    # Windows keeps an existing file's name when it's overwritten; remove it first so a
    # renamed entry (phonnect.lnk -> Phonnect.lnk) gets the new spelling.
    path.unlink(missing_ok=True)
    # Values go in through environment variables to avoid any quoting issues.
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:SAL_LNK);"
        "$s.TargetPath = $env:SAL_TARGET;"
        "$s.Arguments = $env:SAL_ARGS;"
        "$s.WorkingDirectory = $env:USERPROFILE;"
        "$s.Description = 'Phonnect: your phone on your desktop';"
        "if ($env:SAL_ICON) { $s.IconLocation = $env:SAL_ICON + ',0' };"
        "$s.Save()"
    )
    env = dict(
        os.environ,
        SAL_LNK=str(path),
        SAL_TARGET=cmd[0],
        SAL_ARGS=subprocess.list2cmdline(cmd[1:]),
        SAL_ICON=icon,
    )
    subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
        env=env,
        check=True,
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
