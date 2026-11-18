"""Checking GitHub for new releases of Phonnect and scrcpy, and updating Phonnect.

At most one check a day (cached in the state folder). The only data sent is the request
to GitHub's public API. Updating runs the release's own installer script in a terminal
window, so the user sees what happens: it stops the app (which puts phone settings back),
replaces it with uv and starts it again.
"""

from __future__ import annotations

import json
import logging
import re
import shlex
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from phonnect import __version__, paths
from phonnect.osutil import IS_MAC, IS_WINDOWS

log = logging.getLogger(__name__)

PHONNECT_REPO = "3sztof/phonnect"
SCRCPY_REPO = "Genymobile/scrcpy"
CHECK_EVERY = 24 * 3600
RELEASES = f"https://github.com/{PHONNECT_REPO}/releases"


def parse_version(text: str | None) -> tuple[int, ...] | None:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    if not m:
        return None
    return tuple(int(p) for p in m.groups() if p is not None)


def is_newer(latest: str | None, current: str | tuple[int, ...] | None) -> bool:
    new = parse_version(latest)
    old = parse_version(current) if isinstance(current, str) else current
    if new is None or old is None:
        return False
    width = max(len(new), len(old))
    return new + (0,) * (width - len(new)) > tuple(old) + (0,) * (width - len(old))


def latest_release(repo: str, timeout: float = 10) -> str | None:
    """Version of `repo`'s latest GitHub release ("3.4"), or None if it can't be found."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"phonnect/{__version__}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tag = json.load(resp).get("tag_name", "")
    except (OSError, ValueError) as exc:
        log.info("Update check for %s failed: %s", repo, exc)
        return None
    return tag.lstrip("v") or None


@dataclass
class Releases:
    phonnect: str | None = None
    scrcpy: str | None = None
    checked_at: float = 0.0


def cache_file() -> Path:
    return paths.state_dir() / "updates.json"


def load_cache() -> Releases:
    try:
        data = json.loads(cache_file().read_text(encoding="utf-8"))
        return Releases(data.get("phonnect"), data.get("scrcpy"), float(data.get("checked_at", 0)))
    except (OSError, ValueError, TypeError, AttributeError):
        return Releases()


def check(force: bool = False, fetch=latest_release, now=time.time) -> Releases:
    """Latest known releases; asks GitHub only if the last check is older than a day (or `force`)."""
    cached = load_cache()
    if not force and cached.checked_at and now() - cached.checked_at < CHECK_EVERY:
        return cached
    found = Releases(fetch(PHONNECT_REPO), fetch(SCRCPY_REPO), now())
    # A failed request keeps what we knew, and is retried at the next check.
    result = Releases(found.phonnect or cached.phonnect, found.scrcpy or cached.scrcpy, found.checked_at)
    if found.phonnect is None and found.scrcpy is None:
        result.checked_at = cached.checked_at
    try:
        cache_file().parent.mkdir(parents=True, exist_ok=True)
        cache_file().write_text(json.dumps(asdict(result)) + "\n", encoding="utf-8")
    except OSError:
        pass
    log.info("Latest releases: Phonnect %s, scrcpy %s", result.phonnect, result.scrcpy)
    return result


def phonnect_update(releases: Releases) -> str | None:
    """The newer Phonnect version, if there is one."""
    return releases.phonnect if is_newer(releases.phonnect, __version__) else None


def scrcpy_update(releases: Releases, installed: tuple[int, ...] | None) -> str | None:
    return releases.scrcpy if is_newer(releases.scrcpy, installed) else None


def scrcpy_update_hint(scrcpy_path: str | None) -> str:
    """How to update scrcpy, for the way it was most likely installed."""
    p = (scrcpy_path or "").replace("\\", "/").lower()
    if "winget" in p:
        cmd = "winget upgrade Genymobile.scrcpy"
    elif "scoop" in p:
        cmd = "scoop update scrcpy"
    elif "chocolatey" in p:
        cmd = "choco upgrade scrcpy (as admin)"
    elif "/homebrew/" in p or "/usr/local/" in p and IS_MAC:
        cmd = "brew upgrade scrcpy"
    elif "/snap/" in p:
        cmd = "sudo snap refresh scrcpy"
    elif IS_WINDOWS:
        cmd = "download it from https://github.com/Genymobile/scrcpy/releases"
    else:
        cmd = "update it with your package manager"
    return f"To update scrcpy, close the mirror windows, quit Phonnect, then: {cmd}"


def installer_url(version: str, script: str) -> str:
    return f"{RELEASES}/download/v{version}/{script}"


def updater_command(version: str) -> list[str]:
    """Runs the release's installer in update mode, then waits so the window stays readable."""
    if IS_WINDOWS:
        script = (
            f"$env:PHONNECT_UPDATE = '1'; $env:PHONNECT_VERSION = '{version}'; "
            f"irm {installer_url(version, 'install.ps1')} | iex; "
            "Read-Host 'Press Enter to close this window'"
        )
        return ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", script]
    script = (
        f"curl -fsSL {shlex.quote(installer_url(version, 'install.sh'))}"
        f" | sh -s -- --update --version {shlex.quote(version)}"
    )
    return ["sh", "-c", script + "; printf '\\nPress Enter to close this window '; read _"]


def start_update(version: str) -> None:
    """Open a terminal window that updates Phonnect to `version` (it asks to confirm first)."""
    from phonnect.osutil import open_terminal

    log.info("Starting the update to Phonnect %s", version)
    open_terminal(updater_command(version))
