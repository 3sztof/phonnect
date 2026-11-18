"""Thin wrapper around the adb command line."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from scrcpy_autolaunch.osutil import NO_WINDOW

USB = "usb"
WIRELESS = "wireless"
EMULATOR = "emulator"

FIXED_TO_USER_ROTATION = {"default", "enabled", "disabled", "enabled_if_no_auto_rotation"}
# Rotation 1 = 90 degrees. "fixed-to-user-rotation enabled" makes the display follow
# it even when the app in front asks for portrait.
LANDSCAPE = {
    "wm": {"method": "wm", "mode": "lock", "rotation": 1, "fixed": "enabled"},
    "settings": {"method": "settings", "accelerometer_rotation": "0", "user_rotation": "1"},
}


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


def parse_wm_density(text: str) -> dict | None:
    """`wm density` output -> {"physical": 360, "override": 400 or None}."""
    physical = re.search(r"Physical density:\s*(\d+)", text)
    if not physical:
        return None
    override = re.search(r"Override density:\s*(\d+)", text)
    return {"physical": int(physical.group(1)), "override": int(override.group(1)) if override else None}


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

    def wifi_ip(self, serial: str) -> str:
        """The phone's Wi-Fi IPv4 address (works over USB too), or ''."""
        try:
            out = self.run("-s", serial, "shell", "ip", "-f", "inet", "addr", "show", "wlan0", timeout=10).stdout
        except (OSError, subprocess.TimeoutExpired):
            return ""
        m = re.search(r"inet (\d{1,3}(?:\.\d{1,3}){3})/", out)
        return m.group(1) if m else ""

    def tls_port(self, serial: str) -> int:
        """Current Wireless debugging port, or 0 if off or not exposed (newer Android versions hide it)."""
        try:
            out = self.run("-s", serial, "shell", "getprop", "service.adb.tls.port", timeout=10).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            return 0
        return int(out) if out.isdigit() else 0

    def wifi_debugging_enabled(self, serial: str) -> bool | None:
        return self._global_flag(serial, "adb_wifi_enabled")

    # ── display density ──────────────────────────────────────────────────────

    def density_state(self, serial: str) -> dict | None:
        try:
            return parse_wm_density(self.run("-s", serial, "shell", "wm", "density", timeout=10).stdout)
        except (OSError, subprocess.TimeoutExpired):
            return None

    def apply_density(self, serial: str, state: dict) -> bool:
        value = state.get("override")
        args = ["wm", "density", str(int(value))] if value else ["wm", "density", "reset"]
        try:
            return self.run("-s", serial, "shell", *args, timeout=10).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    # ── screen rotation ──────────────────────────────────────────────────────

    def rotation_state(self, serial: str) -> dict | None:
        """The phone's current rotation settings, in a form apply_rotation() can restore."""
        try:
            out = self.run("-s", serial, "shell", "cmd", "window", "user-rotation", timeout=10).stdout.strip()
            m = re.fullmatch(r"(lock|free)\s+(\d)", out)
            if m:  # Android 12+: `cmd window user-rotation`
                fixed = self.run("-s", serial, "shell", "cmd", "window", "fixed-to-user-rotation", timeout=10)
                fixed_value = fixed.stdout.strip()
                return {
                    "method": "wm",
                    "mode": m.group(1),
                    "rotation": int(m.group(2)),
                    "fixed": fixed_value if fixed_value in FIXED_TO_USER_ROTATION else "default",
                }
            accel = self.run("-s", serial, "shell", "settings", "get", "system", "accelerometer_rotation").stdout
            user = self.run("-s", serial, "shell", "settings", "get", "system", "user_rotation").stdout
            return {"method": "settings", "accelerometer_rotation": accel.strip(), "user_rotation": user.strip()}
        except (OSError, subprocess.TimeoutExpired):
            return None

    def apply_rotation(self, serial: str, state: dict) -> bool:
        try:
            if state["method"] == "wm":
                script = (
                    f"cmd window fixed-to-user-rotation {state['fixed']}; "
                    f"cmd window user-rotation {state['mode']} {state['rotation']}"
                )
            else:
                parts = [
                    f"settings put system {key} {state[key]}"
                    for key in ("accelerometer_rotation", "user_rotation")
                    if str(state.get(key, "")).isdigit()
                ]
                script = "; ".join(parts)
            return self.run("-s", serial, "shell", script, timeout=10).returncode == 0
        except (OSError, subprocess.TimeoutExpired, KeyError):
            return False

    def usb_debugging_enabled(self, serial: str) -> bool | None:
        return self._global_flag(serial, "adb_enabled")

    def _global_flag(self, serial: str, name: str) -> bool | None:
        try:
            out = self.run("-s", serial, "shell", "settings", "get", "global", name, timeout=10).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            return None
        return {"1": True, "0": False}.get(out)
