"""Thin wrapper around the adb command line."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from scrcpy_autolaunch.osutil import NO_WINDOW

USB = "usb"
WIRELESS = "wireless"
EMULATOR = "emulator"


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    model: str = ""

    @property
    def online(self) -> bool:
        return self.state == "device"

    @property
    def transport(self) -> str:
        # Same heuristic scrcpy uses: adb on Windows does not print a usb: field.
        if self.serial.startswith("emulator-"):
            return EMULATOR
        if "._adb-tls-connect." in self.serial or "._adb._tcp" in self.serial:
            return WIRELESS
        if re.search(r":\d+$", self.serial):
            return WIRELESS
        return USB

    @property
    def label(self) -> str:
        name = self.model.replace("_", " ") or self.serial
        kind = {USB: "USB", WIRELESS: "Wi-Fi", EMULATOR: "emulator"}[self.transport]
        return f"{name} ({kind})"


@dataclass(frozen=True)
class MdnsService:
    name: str
    service: str
    address: str


def parse_devices(text: str) -> list[Device]:
    devices = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("List of devices", "*", "adb server", "adb:")):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, rest = parts[0], parts[1:]
        if rest[:2] == ["no", "permissions"]:
            state, attrs = "no permissions", []
        else:
            state, attrs = rest[0], rest[1:]
        info = dict(a.split(":", 1) for a in attrs if ":" in a)
        devices.append(Device(serial=serial, state=state, model=info.get("model", "")))
    return devices


def parse_mdns(text: str) -> list[MdnsService]:
    services = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1].startswith("_adb"):
            services.append(MdnsService(name=parts[0], service=parts[1].rstrip("."), address=parts[2]))
    return services


class Adb:
    def __init__(self, path: str):
        self.path = path

    def run(self, *args: str, timeout: float = 15) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.path, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            creationflags=NO_WINDOW,
        )

    def start_server(self) -> None:
        # No pipes here: the daemon this may spawn must not inherit our stdout,
        # or a later read could block until the daemon exits.
        subprocess.run(
            [self.path, "start-server"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            creationflags=NO_WINDOW,
        )

    def devices(self) -> list[Device]:
        return parse_devices(self.run("devices", "-l").stdout)

    def hardware_id(self, serial: str) -> str:
        """Stable per-phone ID, so the same phone over USB and Wi-Fi is one device."""
        try:
            out = self.run("-s", serial, "shell", "getprop", "ro.serialno", timeout=10).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            out = ""
        return out or serial

    def pair(self, address: str, code: str) -> tuple[bool, str]:
        r = self.run("pair", address, code, timeout=30)
        out = (r.stdout + r.stderr).strip()
        return ("Successfully paired" in out, out)

    def connect(self, address: str) -> tuple[bool, str]:
        r = self.run("connect", address, timeout=20)
        out = (r.stdout + r.stderr).strip()
        # Success: "connected to X" / "already connected to X".
        # Failure: "failed to connect to X" / "cannot connect to X".
        return ("connected to" in out, out)

    def disconnect(self, address: str | None = None) -> str:
        r = self.run("disconnect", *([address] if address else []), timeout=15)
        return (r.stdout + r.stderr).strip()

    def mdns_services(self) -> list[MdnsService]:
        return parse_mdns(self.run("mdns", "services", timeout=15).stdout)
