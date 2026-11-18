"""Command line interface: `scrcpy-autolaunch <command>`."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import signal
import sys
import time
from pathlib import Path

from scrcpy_autolaunch import __version__, autostart, paths
from scrcpy_autolaunch.adb import WIRELESS, Adb
from scrcpy_autolaunch.config import Config
from scrcpy_autolaunch.instance import InstanceLock, running_pid
from scrcpy_autolaunch.logsetup import setup_logging
from scrcpy_autolaunch.osutil import IS_LINUX, IS_WINDOWS, spawn_detached
from scrcpy_autolaunch.tools import find_tool, install_hint, scrcpy_version

log = logging.getLogger("scrcpy_autolaunch")


# ── shared helpers ───────────────────────────────────────────────────────────


def resolve_tools(cfg: Config):
    scrcpy = find_tool("scrcpy", cfg.scrcpy_path)
    adb = find_tool("adb", cfg.adb_path, near=scrcpy)
    problem = None
    missing = [name for name, path in (("scrcpy", scrcpy), ("adb", adb)) if not path]
    if missing:
        problem = f"{' and '.join(missing)} not found. Install with: {install_hint()}"
    version = scrcpy_version(scrcpy) if scrcpy else None
    return adb, scrcpy, version, problem


def require_adb(cfg: Config) -> Adb:
    adb, _, _, problem = resolve_tools(cfg)
    if not adb:
        sys.exit(problem)
    return Adb(adb)


def legacy_startup_entry() -> Path | None:
    """The PowerShell/VBS version from the legacy-windows branch, if installed."""
    if not IS_WINDOWS:
        return None
    vbs = autostart.entry_path().with_name("scrcpy-auto-launch.vbs")
    return vbs if vbs.exists() else None


# ── commands ─────────────────────────────────────────────────────────────────


def cmd_run(args) -> int:
    setup_logging(to_file=True, to_console=True)
    lock = InstanceLock()
    if not lock.acquire():
        print(f"Already running (pid {running_pid()}). Stop it with: scrcpy-autolaunch stop")
        return 1
    with lock:
        cfg = Config.load()
        adb, scrcpy, version, problem = resolve_tools(cfg)
        if problem:
            log.error(problem)
            return 1
        from scrcpy_autolaunch.watcher import Watcher

        watcher = Watcher(cfg, Adb(adb), scrcpy, version)
        try:
            watcher.run_forever()
        except KeyboardInterrupt:
            watcher.stop()
    return 0


def cmd_tray(args) -> int:
    lock = InstanceLock()
    if not lock.acquire():
        if sys.stderr is not None:
            print(f"Already running (pid {running_pid()}).", file=sys.stderr)
        return 0
    with lock:
        setup_logging(to_file=True, to_console=True)
        try:
            cfg = Config.load()
            adb, scrcpy, version, problem = resolve_tools(cfg)
            if problem:
                log.error(problem)
            from scrcpy_autolaunch.tray import run_tray

            run_tray(cfg, Adb(adb) if adb else None, scrcpy, version, problem)
        except Exception:
            log.exception("Tray crashed")
            return 1
    return 0


def cmd_start(args) -> int:
    pid = running_pid()
    if pid is not None:
        print(f"Already running (pid {pid}).")
        return 0
    cmd = autostart.tray_command()
    spawn_detached(cmd)
    for _ in range(50):
        time.sleep(0.1)
        if (pid := running_pid()) is not None:
            print(f"Started (pid {pid}). Look for the phone icon in the tray / menu bar.")
            return 0
    print(f"The tray app did not start. Check the log: {paths.log_file()}")
    return 1


def cmd_stop(args) -> int:
    pid = running_pid()
    if pid is None:
        print("Not running.")
        return 0
    if pid < 0:
        print(f"Running, but the PID is unknown. Delete {paths.lock_file()} after ending the process manually.")
        return 1
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        print(f"Could not stop pid {pid}: {exc}")
        return 1
    for _ in range(50):
        if running_pid() is None:
            print(f"Stopped (pid {pid}). Open scrcpy windows stay open.")
            return 0
        time.sleep(0.1)
    print(f"pid {pid} is still running.")
    return 1


def cmd_status(args) -> int:
    pid = running_pid()
    cfg = Config.load()
    adb, scrcpy, version, problem = resolve_tools(cfg)
    print(f"running:        {'yes, pid ' + str(pid) if pid is not None else 'no'}")
    print(f"start at login: {'yes, ' + str(autostart.entry_path()) if autostart.is_enabled() else 'no'}")
    print(f"auto-launch:    USB {'on' if cfg.auto_usb else 'off'}, Wi-Fi {'on' if cfg.auto_wireless else 'off'}")
    print(f"scrcpy:         {scrcpy or 'NOT FOUND'}{'  (v%d.%d)' % version if version else ''}")
    print(f"adb:            {adb or 'NOT FOUND'}")
    print(f"config:         {paths.config_file()}")
    print(f"log:            {paths.log_file()}")
    return 1 if problem else 0


def cmd_doctor(args) -> int:
    ok = True
    print(f"scrcpy-autolaunch {__version__}, Python {sys.version.split()[0]} ({sys.executable})")
    cfg = Config.load()
    adb, scrcpy, version, problem = resolve_tools(cfg)
    print(f"scrcpy: {scrcpy or 'NOT FOUND'}")
    print(f"adb:    {adb or 'NOT FOUND'}")
    if problem:
        print(f"\nProblem: {problem}")
        return 1
    if version is None:
        print("warning: could not read the scrcpy version")
    elif version < (2, 0):
        print(f"warning: scrcpy {version[0]}.{version[1]} is old; 2.0 or newer is recommended")
    else:
        print(f"scrcpy version {version[0]}.{version[1]}: ok")

    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401

        print("tray libraries: ok")
    except Exception as exc:
        ok = False
        print(f"tray libraries: FAILED ({exc})")
        if IS_LINUX:
            print("  Linux needs a tray: on GNOME install the 'AppIndicator and KStatusNotifierItem' extension.")

    devices = Adb(adb).devices()
    if not devices:
        print("devices: none connected (plug in the phone with USB debugging enabled)")
    for d in devices:
        print(f"device: {d.label} [{d.serial}] state={d.state}")
        if d.state == "unauthorized":
            print("  -> accept the 'Allow USB debugging' prompt on the phone")
        elif d.state == "no permissions":
            ok = False
            print("  -> adb can't access the USB device; see the Linux section of the README")

    if (legacy := legacy_startup_entry()) is not None:
        print(f"warning: the old PowerShell watcher is still set to start at login: {legacy}")
        print("  It would open a second scrcpy window. Remove it (see README, 'Migrating from legacy').")
    return 0 if ok else 1


def cmd_install(args) -> int:
    path = autostart.enable()
    print(f"Start at login enabled: {path}")
    if (legacy := legacy_startup_entry()) is not None:
        print(f"warning: old PowerShell watcher found in Startup: {legacy} (see README, 'Migrating from legacy')")
    if args.no_start:
        return 0
    return cmd_start(args)


def cmd_uninstall(args) -> int:
    cmd_stop(args)
    if autostart.disable():
        print(f"Removed start-at-login entry: {autostart.entry_path()}")
    if args.purge:
        for d in {paths.config_dir(), paths.state_dir()}:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
                print(f"Deleted {d}")
    return 0


def cmd_devices(args) -> int:
    devices = require_adb(Config.load()).devices()
    if not devices:
        print("No devices.")
    for d in devices:
        print(f"{d.serial:40} {d.transport:9} {d.state:15} {d.model}")
    return 0


def cmd_pair(args) -> int:
    adb = require_adb(Config.load())
    if not args.address:
        return _dialog(adb, "pair")
    code = args.code or input("Pairing code: ").strip()
    ok, out = adb.pair(args.address, code)
    print(out)
    return 0 if ok else 1


def cmd_connect(args) -> int:
    adb = require_adb(Config.load())
    if not args.address:
        return _dialog(adb, "connect")
    ok, out = adb.connect(args.address)
    print(out)
    return 0 if ok else 1


def cmd_disconnect(args) -> int:
    print(require_adb(Config.load()).disconnect(args.address) or "Done.")
    return 0


def cmd_discover(args) -> int:
    adb = require_adb(Config.load())
    services = adb.mdns_services()
    if not services:
        print("Nothing found. Turn on Wireless debugging on the phone.")
        return 1
    for s in services:
        print(f"{s.service:24} {s.address:22} {s.name}")
    if args.connect:
        for s in services:
            if "tls-connect" in s.service:
                print(adb.connect(s.address)[1])
    connected = [d for d in adb.devices() if d.transport == WIRELESS]
    print(f"{len(connected)} Wi-Fi device(s) connected.")
    return 0


def cmd_log(args) -> int:
    path = paths.log_file()
    if not path.exists():
        print(f"No log yet ({path}).")
        return 0
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    print("\n".join(lines[-args.lines :]))
    return 0


def cmd_dialog(args) -> int:
    return _dialog(require_adb(Config.load()), args.kind)


def _dialog(adb: Adb, kind: str) -> int:
    from scrcpy_autolaunch.dialogs import run_dialog

    code = run_dialog(kind, adb)
    if code == 3 and sys.stderr is not None:
        print("Tk is not available; pass the address on the command line instead.", file=sys.stderr)
    return code


# ── entry points ─────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scrcpy-autolaunch",
        description="Open scrcpy automatically when an Android device connects.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    def add(name, func, help, **kw):
        sp = sub.add_parser(name, help=help, **kw)
        sp.set_defaults(func=func)
        return sp

    add("tray", cmd_tray, "run the tray icon and watcher in the foreground")
    add("run", cmd_run, "run the watcher without a tray icon (logs to the console)")
    add("start", cmd_start, "start the tray app in the background")
    add("stop", cmd_stop, "stop the running tray app / watcher")
    add("status", cmd_status, "show whether it is running and where files are")
    add("doctor", cmd_doctor, "check scrcpy, adb, tray support and devices")
    add("install", cmd_install, "enable start at login and start now").add_argument(
        "--no-start", action="store_true", help="only register start at login"
    )
    add("uninstall", cmd_uninstall, "stop, disable start at login").add_argument(
        "--purge", action="store_true", help="also delete settings and logs"
    )
    add("devices", cmd_devices, "list devices known to adb")
    sp = add("pair", cmd_pair, "pair a phone for wireless debugging (opens a dialog without arguments)")
    sp.add_argument("address", nargs="?", help="IP:PORT from 'Pair device with pairing code'")
    sp.add_argument("code", nargs="?", help="6-digit pairing code")
    add("connect", cmd_connect, "connect to a paired phone over Wi-Fi").add_argument(
        "address", nargs="?", help="IP:PORT shown on the Wireless debugging screen"
    )
    add("disconnect", cmd_disconnect, "disconnect Wi-Fi devices").add_argument(
        "address", nargs="?", help="only this IP:PORT (default: all)"
    )
    add("discover", cmd_discover, "find phones with Wireless debugging on the network").add_argument(
        "--connect", action="store_true", help="also connect to them"
    )
    add("log", cmd_log, "print the end of the log").add_argument(
        "-n", "--lines", type=int, default=30, help="number of lines (default 30)"
    )
    add("_dialog", cmd_dialog, argparse.SUPPRESS).add_argument("kind", choices=["pair", "connect"])
    # Hide the internal command from --help.
    sub._choices_actions = [a for a in sub._choices_actions if a.dest != "_dialog"]
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        sys.exit(0)
    sys.exit(args.func(args))


def tray_main() -> None:
    """Entry point of the windowless `scrcpy-autolaunch-tray` executable."""
    sys.exit(cmd_tray(None))
