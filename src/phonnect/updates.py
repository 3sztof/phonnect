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
# Release versions as published: digits and dots only. Anything else (from the API or the
# cache file) is rejected, because the version ends up in the updater's command line.
STRICT_VERSION_RE = re.compile(r"\d{1,4}(\.\d{1,4}){1,3}")


def strict_version(text: str | None) -> str | None:
    """`text` as a plain version ("1.2.3", a leading "v" allowed), or None if it's anything else."""
    if not isinstance(text, str):
        return None
    candidate = text.strip()
    candidate = candidate[1:] if candidate[:1] in ("v", "V") else candidate
    return candidate if STRICT_VERSION_RE.fullmatch(candidate) else None


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
    except (OSError, ValueError, AttributeError) as exc:
        log.info("Update check for %s failed: %s", repo, exc)
        return None
    version = strict_version(tag)
    if version is None:
        log.warning("Ignoring the latest release of %s: unexpected tag %r", repo, str(tag)[:40])
    return version


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
        return Releases(
            strict_version(data.get("phonnect")), strict_version(data.get("scrcpy")), float(data.get("checked_at", 0))
        )
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


def updater_command(version: str, confirm: bool = True) -> list[str]:
    """Runs the release's installer in update mode.

    confirm=False answers yes (the user already clicked Update). The window closes by itself
    a few seconds after a successful update, and stays open after a failure so it can be read.
    Raises ValueError for anything but a plain version: it goes into a command line.
    """
    checked = strict_version(version)
    if checked is None:
        raise ValueError(f"not a release version: {version!r}")
    version = checked
    if IS_WINDOWS:
        yes = "" if confirm else "$env:PHONNECT_YES = '1'; "
        script = (
            f"$env:PHONNECT_UPDATE = '1'; $env:PHONNECT_VERSION = '{version}'; {yes}"
            "$env:PHONNECT_RESULT = ''; "
            f"irm '{installer_url(version, 'install.ps1')}' | iex; "
            "if ($env:PHONNECT_RESULT -eq 'ok') { Start-Sleep 5 } "
            "else { Read-Host 'Press Enter to close this window' }"
        )
        return ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", script]
    flags = "--update --version " + shlex.quote(version) + ("" if confirm else " --yes")
    script = (
        f"if curl -fsSL {shlex.quote(installer_url(version, 'install.sh'))} | sh -s -- {flags}; "
        "then sleep 5; else printf '\\nPress Enter to close this window '; read _; fi"
    )
    return ["sh", "-c", script]


def start_update(version: str, confirm: bool = True) -> None:
    """Open a terminal window that updates Phonnect to `version`."""
    from phonnect.osutil import open_terminal

    log.info("Starting the update to Phonnect %s", version)
    open_terminal(updater_command(version, confirm))
