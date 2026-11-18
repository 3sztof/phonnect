"""Per-OS locations for config, log and lock files.

Windows: %LOCALAPPDATA%\\phonnect
macOS:   ~/Library/Application Support/phonnect
Linux:   $XDG_CONFIG_HOME/phonnect (config)
         $XDG_STATE_HOME/phonnect  (log, lock)

PHONNECT_HOME overrides all of them (used by tests and for portable setups).
The app used to be called scrcpy-autolaunch; migrate_from_legacy() moves its folders.
"""

from __future__ import annotations

import os
from pathlib import Path

from phonnect.osutil import IS_MAC, IS_WINDOWS

APP = "phonnect"
LEGACY_APP = "scrcpy-autolaunch"


def _override() -> Path | None:
    value = os.environ.get("PHONNECT_HOME")
    return Path(value) if value else None


def config_dir(app: str = APP) -> Path:
    if (o := _override()) is not None:
        return o
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif IS_MAC:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / app


def state_dir(app: str = APP) -> Path:
    if (o := _override()) is not None:
        return o
    if IS_WINDOWS or IS_MAC:
        return config_dir(app)
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / app


def config_file() -> Path:
    return config_dir() / "config.json"


def log_file() -> Path:
    return state_dir() / "phonnect.log"


def lock_file() -> Path:
    return state_dir() / "instance.lock"


def pid_file() -> Path:
    return state_dir() / "instance.pid"


def migrate_from_legacy() -> list[str]:
    """Move scrcpy-autolaunch's folders to Phonnect's, once. Returns what was done (for messages).

    Covers settings, remembered phones, and phone settings still waiting to be restored.
    Nothing happens if Phonnect already has its own data.
    """
    if _override() is not None:
        return []
    done: list[str] = []
    for kind in (config_dir, state_dir):
        old, new = kind(LEGACY_APP), kind(APP)
        if old == new or not old.is_dir():
            continue
        if new.exists() and any(new.iterdir()):
            continue
        try:
            new.parent.mkdir(parents=True, exist_ok=True)
            if new.exists():
                new.rmdir()
            old.rename(new)
        except OSError as exc:
            done.append(f"could not move {old} to {new}: {exc}")
            continue
        legacy_log = new / f"{LEGACY_APP}.log"
        if legacy_log.exists() and not (new / "phonnect.log").exists():
            try:
                legacy_log.rename(new / "phonnect.log")
            except OSError:
                pass
        done.append(f"moved {old} to {new}")
    return done
