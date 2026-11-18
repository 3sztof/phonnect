"""Per-OS locations for config, log and lock files.

Windows: %LOCALAPPDATA%\\scrcpy-autolaunch
macOS:   ~/Library/Application Support/scrcpy-autolaunch
Linux:   $XDG_CONFIG_HOME/scrcpy-autolaunch (config)
         $XDG_STATE_HOME/scrcpy-autolaunch  (log, lock)

SCRCPY_AUTOLAUNCH_HOME overrides all of them (used by tests and for portable setups).
"""

from __future__ import annotations

import os
from pathlib import Path

from scrcpy_autolaunch.osutil import IS_MAC, IS_WINDOWS

APP = "scrcpy-autolaunch"


def _override() -> Path | None:
    value = os.environ.get("SCRCPY_AUTOLAUNCH_HOME")
    return Path(value) if value else None


def config_dir() -> Path:
    if (o := _override()) is not None:
        return o
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif IS_MAC:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP


def state_dir() -> Path:
    if (o := _override()) is not None:
        return o
    if IS_WINDOWS or IS_MAC:
        return config_dir()
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / APP


def config_file() -> Path:
    return config_dir() / "config.json"


def log_file() -> Path:
    return state_dir() / "scrcpy-autolaunch.log"


def lock_file() -> Path:
    return state_dir() / "instance.lock"


def pid_file() -> Path:
    return state_dir() / "instance.pid"
