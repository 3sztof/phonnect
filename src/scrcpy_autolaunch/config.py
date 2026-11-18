"""User settings, stored as JSON. Unknown keys are ignored; missing keys get defaults."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from scrcpy_autolaunch import paths

log = logging.getLogger(__name__)


@dataclass
class Config:
    auto_usb: bool = True
    auto_wireless: bool = False
    # Adds --keyboard=uhid: scrcpy acts as a physical keyboard, so Android hides
    # the on-screen keyboard while mirroring. Nothing changes on the phone permanently.
    hide_phone_keyboard: bool = True
    # Rotate the phone to landscape while it's mirrored (even apps that ask for
    # portrait); the previous rotation setting is restored when the window closes.
    force_landscape: bool = False
    # Closing a Wi-Fi mirror window also disconnects that phone's Wi-Fi debugging
    # connection, unless this is on.
    keep_wifi_connected: bool = False
    # "off":  --no-audio, sound stays on the phone only (default)
    # "both": play on the PC *and* keep playing on the phone (Android 13+; apps may opt out)
    # "pc":   move sound to the PC; the phone goes silent (also e.g. a Bluetooth amp)
    audio: str = "off"
    scrcpy_args: list[str] = field(default_factory=lambda: ["--stay-awake"])
    # Extra args for Wi-Fi connections: less bandwidth, less 2.4 GHz contention
    # with Bluetooth.
    wireless_extra_args: list[str] = field(
        default_factory=lambda: ["--max-size=1600", "--video-bit-rate=6M"]
    )
    poll_interval: float = 1.0
    adb_path: str | None = None
    scrcpy_path: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or paths.config_file()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        except (OSError, ValueError) as exc:
            log.warning("Ignoring unreadable config %s: %s", path, exc)
            return cls()
        if not isinstance(data, dict):
            log.warning("Ignoring config %s: not a JSON object", path)
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path | None = None) -> None:
        path = path or paths.config_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
