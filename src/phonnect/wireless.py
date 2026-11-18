"""Remember Wi-Fi phones and reconnect to them.

Android picks a new port every time Wireless debugging is turned on, so a saved
IP:port goes stale. Reconnecting therefore tries, in order:
1. mDNS: the phone advertises its current port (fast, but some networks block it)
2. the last address that worked
3. a TCP scan of the phone's last known IP for the debugging port
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from phonnect import paths
from phonnect.adb import WIRELESS, Adb

log = logging.getLogger(__name__)

# adb pairs with a phone under the name "adb-<ro.serialno>-<6 random chars>".
PAIRED_NAME_RE = re.compile(rb"adb-([A-Za-z0-9]+)-[A-Za-z0-9]{6}")
IP_PORT_RE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3}):(\d+)$")

# adbd binds the debugging port to a random port from the Linux ephemeral range.
SCAN_PORTS = range(32768, 61000)


def android_user_home() -> Path:
    if os.environ.get("ANDROID_USER_HOME"):
        return Path(os.environ["ANDROID_USER_HOME"])
    if os.environ.get("ANDROID_SDK_HOME"):
        return Path(os.environ["ANDROID_SDK_HOME"]) / ".android"
    return Path.home() / ".android"


def paired_serials(path: Path | None = None) -> set[str]:
    """Hardware serials of phones this computer's adb has paired with."""
    path = path or android_user_home() / "adb_known_hosts.pb"
    try:
        data = path.read_bytes()
    except OSError:
        return set()
    return {m.group(1).decode("ascii") for m in PAIRED_NAME_RE.finditer(data)}


def split_address(address: str) -> tuple[str, int] | None:
    m = IP_PORT_RE.match(address)
    return (m.group(1), int(m.group(2))) if m else None


@dataclass
class KnownDevice:
    hw_id: str
    model: str = ""
    address: str = ""  # last IP:port that worked
    ip: str = ""  # last known Wi-Fi IP (also learned while on USB)
    last_seen: float = 0.0

    @property
    def label(self) -> str:
        if self.model:
            return self.model.replace("_", " ")
        return f"Phone {self.hw_id[:8]}…" if len(self.hw_id) > 9 else f"Phone {self.hw_id}"


class KnownDevices:
    """Phones seen before, saved in wireless-devices.json, merged with adb's paired list."""

    def __init__(self, path: Path | None = None, paired: Callable[[], set[str]] = paired_serials):
        self.path = path or paths.state_dir() / "wireless-devices.json"
        self._paired = paired
        self._lock = threading.Lock()
        self._mtime = self._file_mtime()
        self._devices: dict[str, KnownDevice] = self._load()

    def _file_mtime(self) -> float:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return 0.0

    def _reload_if_changed(self) -> None:
        """The Wi-Fi window runs in another process and may have updated the file."""
        mtime = self._file_mtime()
        if mtime != self._mtime:
            self._mtime = mtime
            self._devices = self._load()

    def _load(self) -> dict[str, KnownDevice]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        names = {f.name for f in fields(KnownDevice)}
        out = {}
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, dict) and item.get("hw_id"):
                d = KnownDevice(**{k: v for k, v in item.items() if k in names})
                out[d.hw_id] = d
        return out

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(d) for d in self._devices.values()], indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def remember(self, hw_id: str, model: str = "", address: str = "", ip: str = "") -> None:
        with self._lock:
            self._reload_if_changed()
            d = self._devices.get(hw_id) or KnownDevice(hw_id)
            d.model = model or d.model
            parsed = split_address(address) if address else None
            if parsed:
                d.address = address
                d.ip = parsed[0]
            d.ip = ip or d.ip
            d.last_seen = time.time()
            self._devices[hw_id] = d
            try:
                self._save()
                self._mtime = self._file_mtime()
            except OSError as exc:
                log.warning("Could not save %s: %s", self.path, exc)

    def all(self) -> list[KnownDevice]:
        """Remembered phones, plus paired phones never seen by this app."""
        with self._lock:
            self._reload_if_changed()
            devices = dict(self._devices)
        for serial in self._paired():
            devices.setdefault(serial, KnownDevice(serial))
        return sorted(devices.values(), key=lambda d: (-d.last_seen, d.label))

    def get(self, hw_id: str) -> KnownDevice | None:
        return next((d for d in self.all() if d.hw_id == hw_id), None)


def wireless_serial_for(device: KnownDevice, adb_devices) -> str | None:
    """The adb serial of this phone's Wi-Fi connection, if adb has one (any state)."""
    for d in adb_devices:
        if d.transport != WIRELESS:
            continue
        if d.serial.startswith(f"adb-{device.hw_id}-"):
            return d.serial
        if device.address and d.serial == device.address:
            return d.serial
        if device.ip and d.serial.startswith(device.ip + ":"):
            return d.serial
    return None


def status_of(device: KnownDevice, adb_devices) -> str:
    """'Wi-Fi', 'Wi-Fi (offline)', 'USB' or 'not connected'."""
    adb_devices = list(adb_devices)
    serial = wireless_serial_for(device, adb_devices)
    if serial is not None:
        state = next(d.state for d in adb_devices if d.serial == serial)
        return "Wi-Fi" if state == "device" else f"Wi-Fi ({state})"
    if any(d.serial == device.hw_id and d.online for d in adb_devices):
        return "USB"
    return "not connected"


def paired_guid(pair_output: str) -> str | None:
    """Hardware serial from `adb pair` output: '... [guid=adb-<serial>-xxxxxx]'."""
    m = re.search(r"guid=adb-([A-Za-z0-9]+)-[A-Za-z0-9]{6}", pair_output)
    return m.group(1) if m else None


# ── connecting ───────────────────────────────────────────────────────────────


def connect_verified(adb: Adb, address: str, wait: float = 4.0) -> tuple[bool, str]:
    """`adb connect`, then confirm the device actually comes online (not 'offline')."""
    ok, out = adb.connect(address)
    if not ok:
        return False, out
    deadline = time.monotonic() + wait
    state = ""
    while time.monotonic() < deadline:
        state = next((d.state for d in adb.devices() if d.serial == address), "")
        if state == "device":
            return True, out
        time.sleep(0.5)
    adb.disconnect(address)
    return (
        False,
        f"{address} connected but stayed '{state or 'missing'}' (wrong port, or the phone rejected this computer)",
    )


def drop_offline(adb: Adb, ip: str | None = None) -> None:
    """Disconnect stale 'offline' Wi-Fi entries so they don't block a fresh connect."""
    for d in adb.devices():
        if d.transport == WIRELESS and not d.online and (ip is None or d.serial.startswith(ip + ":")):
            log.info("Dropping stale %s entry %s", d.state, d.serial)
            adb.disconnect(d.serial)


def scan_ports(ip: str, ports=SCAN_PORTS, timeout: float = 0.5, concurrency: int = 1500) -> list[int]:
    """Open TCP ports on `ip` within `ports`."""

    async def probe(port: int, sem: asyncio.Semaphore) -> int | None:
        async with sem:
            try:
                _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout)
            except (TimeoutError, OSError):
                return None
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
            return port

    async def run() -> list[int]:
        sem = asyncio.Semaphore(concurrency)
        results = await asyncio.gather(*(probe(p, sem) for p in ports))
        return [p for p in results if p]

    return asyncio.run(run())


def mdns_address(adb: Adb, hw_id: str) -> str | None:
    try:
        services = adb.mdns_services()
    except (OSError, subprocess.TimeoutExpired):
        return None
    for s in services:
        if "tls-connect" in s.service and s.name.startswith(f"adb-{hw_id}-"):
            return s.address
    return None


# ── pairing with a QR code ───────────────────────────────────────────────────
# Android 11+: Wireless debugging > "Pair device with QR code". The QR code holds a
# service name and a password we make up. After scanning it, the phone advertises a
# pairing service with that name over mDNS; we pair with its address and the password.


@dataclass(frozen=True)
class QrPairing:
    name: str
    password: str

    @property
    def text(self) -> str:
        return f"WIFI:T:ADB;S:{self.name};P:{self.password};;"


def new_qr_pairing() -> QrPairing:
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    return QrPairing(
        name="phonnect-" + "".join(secrets.choice(alphabet) for _ in range(8)),
        password="".join(secrets.choice(alphabet) for _ in range(12)),
    )


def qr_pairing_address(adb: Adb, pairing: QrPairing) -> str | None:
    """The phone's pairing address once it has scanned the code, else None."""
    try:
        services = adb.mdns_services()
    except (OSError, subprocess.TimeoutExpired):
        return None
    for s in services:
        if "tls-pairing" in s.service and s.name == pairing.name and split_address(s.address):
            return s.address
    return None


def wait_for_qr_scan(
    adb: Adb, pairing: QrPairing, cancelled: Callable[[], bool], timeout: float = 300, interval: float = 1.0
) -> str | None:
    """Poll mDNS until the phone shows up (it scanned the code), the caller gives up, or `timeout`."""
    deadline = time.monotonic() + timeout
    while not cancelled() and time.monotonic() < deadline:
        if address := qr_pairing_address(adb, pairing):
            return address
        time.sleep(interval)
    return None


def pair_and_connect(
    adb: Adb, known: KnownDevices, address: str, code: str, progress: Callable[[str], None] = lambda msg: None
) -> tuple[bool, str]:
    """Pair with the phone at `address`, remember it, then connect. Returns (ok, message)."""
    progress("Pairing…")
    ok, out = adb.pair(address, code)
    if not ok:
        return False, f"Pairing failed:\n{out or 'no output from adb'}"
    hw = paired_guid(out)
    ip = split_address(address)[0] if split_address(address) else ""
    if not hw:
        return True, "Paired. Now use Connect in the Wi-Fi devices window."
    known.remember(hw, ip=ip)
    progress("Paired. Connecting (this can take up to 30 seconds)…")
    time.sleep(2)  # give the phone a moment to advertise its connect port
    device = known.get(hw)
    ok, result = reconnect(adb, device, progress=progress) if device else (False, "not remembered")
    if ok:
        known.remember(hw, model=adb_model(adb, result), address=result)
        return True, f"Paired and connected ({result})."
    return (
        True,
        f"Paired, but could not connect yet:\n{result}\n\n"
        "Try Connect to address with the port from the Wireless debugging screen.",
    )


def adb_model(adb: Adb, serial: str) -> str:
    try:
        return adb.run("-s", serial, "shell", "getprop", "ro.product.model", timeout=10).stdout.strip()
    except Exception:
        return ""


def reconnect(
    adb: Adb,
    device: KnownDevice,
    scan: bool | None = None,
    progress: Callable[[str], None] = lambda msg: None,
) -> tuple[bool, str]:
    """Connect to a known phone. Returns (ok, address or explanation); never raises for adb trouble.

    scan=None follows the wifi_port_scan setting.
    """
    if scan is None:
        from phonnect.config import Config

        scan = Config.load().wifi_port_scan
    try:
        return _reconnect(adb, device, scan, progress)
    except subprocess.TimeoutExpired as exc:
        log.warning("Connecting to %s: adb timed out: %s", device.label, exc)
        return (
            False,
            f"adb didn't answer within {exc.timeout:.0f} s. "
            "Try again; if it keeps happening, replug or restart the phone.",
        )
    except OSError as exc:
        log.warning("Connecting to %s failed: %s", device.label, exc)
        return False, f"Could not run adb: {exc}"


def _reconnect(adb: Adb, device: KnownDevice, scan: bool, progress: Callable[[str], None]) -> tuple[bool, str]:
    tried: list[str] = []
    drop_offline(adb, device.ip or None)

    if addr := mdns_address(adb, device.hw_id):
        ok, out = connect_verified(adb, addr)
        if ok:
            return True, addr
        tried.append(f"mDNS {addr}: {out}")
    else:
        tried.append("mDNS: phone not advertised")

    if device.address:
        ok, out = connect_verified(adb, device.address)
        if ok:
            return True, device.address
        tried.append(f"last address {device.address}: {out}")

    ip = device.ip
    if scan and ip:
        progress(f"Scanning {ip} for the debugging port…")
        started = time.monotonic()
        open_ports = scan_ports(ip)
        log.info("Port scan of %s: %s open in %.1fs", ip, open_ports or "none", time.monotonic() - started)
        for port in open_ports[:5]:
            addr = f"{ip}:{port}"
            ok, out = connect_verified(adb, addr)
            if ok:
                return True, addr
            tried.append(f"{addr}: {out}")
        if not open_ports:
            tried.append(f"scan of {ip}: no open ports")
    elif not ip:
        tried.append("no known IP address to scan yet")
    else:
        tried.append("port scan turned off in the settings")

    return False, "\n".join(tried)
