"""Locate the adb and scrcpy executables.

Autostart environments often have a minimal PATH (especially macOS LaunchAgents),
so after PATH we also look in the usual install locations for each OS.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from phonnect.osutil import IS_MAC, IS_WINDOWS, NO_WINDOW


def _exe(name: str) -> str:
    return name + ".exe" if IS_WINDOWS else name


def _search_dirs() -> list[Path]:
    home = Path.home()
    if IS_WINDOWS:
        local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        winget = sorted(
            (local / "Microsoft" / "WinGet" / "Packages").glob("Genymobile.scrcpy_*/scrcpy-win64-*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [
            *winget,
            home / "scoop" / "apps" / "scrcpy" / "current",
            home / "scoop" / "shims",
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "chocolatey" / "bin",
            local / "Android" / "Sdk" / "platform-tools",
        ]
    if IS_MAC:
        return [
            Path("/opt/homebrew/bin"),
            Path("/usr/local/bin"),
            home / "Library" / "Android" / "sdk" / "platform-tools",
        ]
    return [
        Path("/usr/local/bin"),
        Path("/usr/bin"),
        Path("/snap/bin"),
        home / ".local" / "bin",
        home / "Android" / "Sdk" / "platform-tools",
    ]


def find_tool(name: str, override: str | None = None, near: str | None = None) -> str | None:
    """Return the full path of `name`, or None.

    Order: explicit override, PATH, next to `near` (scrcpy's Windows release
    bundles adb.exe), then well-known install directories.
    """
    if override:
        return override if Path(override).is_file() else None
    found = shutil.which(name)
    if found:
        return str(Path(found).resolve())
    candidates = [Path(near).parent / _exe(name)] if near else []
    candidates += [d / _exe(name) for d in _search_dirs()]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def scrcpy_version(scrcpy: str) -> tuple[int, int] | None:
    try:
        out = subprocess.run(
            [scrcpy, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=15,
            creationflags=NO_WINDOW,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    return parse_scrcpy_version(out)


def parse_scrcpy_version(text: str) -> tuple[int, int] | None:
    m = re.search(r"scrcpy\s+v?(\d+)\.(\d+)", text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def install_hint() -> str:
    if IS_WINDOWS:
        return "winget install Genymobile.scrcpy   (includes adb)"
    if IS_MAC:
        return "brew install scrcpy && brew install --cask android-platform-tools"
    return "sudo apt install scrcpy adb   (or your distro's equivalent; scrcpy >= 2.0 recommended)"
