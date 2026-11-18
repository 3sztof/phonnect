"""Command line interface: `phonnect <command>`."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import signal
import sys
import time
from pathlib import Path

from phonnect import __version__, autostart, paths
from phonnect.adb import WIRELESS, Adb
from phonnect.config import Config
from phonnect.instance import InstanceLock, running_pid
from phonnect.logsetup import setup_logging
from phonnect.osutil import IS_LINUX, IS_WINDOWS, spawn_detached
from phonnect.tools import find_tool, install_hint, scrcpy_version

log = logging.getLogger("phonnect")


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


def attach_helpers(watcher):
    """Give a watcher what the tray and `run` both need: setting keepers, the
    control server for sidebars, and themed scrcpy title bars."""
    from phonnect.control import ControlServer
    from phonnect.phone_state import DensityKeeper, RotationKeeper

    watcher.rotation = RotationKeeper(watcher.adb, watcher.online_serial)
    watcher.density = DensityKeeper(watcher.adb, watcher.online_serial)
    try:
        server = ControlServer(watcher.handle_control).start()
        watcher.control = (server.address, server.token)
        from phonnect.control import write_endpoint

        write_endpoint(server.address, server.token)
    except OSError as exc:
        log.warning("Sidebars are unavailable (could not open a local port): %s", exc)
    watcher.style_windows = True
    if IS_WINDOWS and Config.load().remember_window:
        from phonnect.window_memory import WindowMemory

        watcher.windows = WindowMemory()


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
        print(f"Already running (pid {running_pid()}). Stop it with: phonnect stop")
        return 1
    with lock:
        cfg = Config.load()
        adb, scrcpy, version, problem = resolve_tools(cfg)
        if problem:
            log.error(problem)
            return 1
        from phonnect.watcher import Watcher

        watcher = Watcher(cfg, Adb(adb), scrcpy, version)
        attach_helpers(watcher)
        watcher.on_quit = watcher.stop
        try:
            watcher.run_forever()
            watcher.restore_all_phone_settings()
        except KeyboardInterrupt:
            watcher.stop()
            watcher.restore_all_phone_settings()
        finally:
            from phonnect.control import remove_endpoint

            remove_endpoint()
    return 0


def cmd_tray(args) -> int:
    lock = InstanceLock()
    if not lock.acquire():
        if sys.stderr is not None:
            print(f"Already running (pid {running_pid()}).", file=sys.stderr)
        # Opened again from the app menu: let the running copy show itself, so it isn't
        # mistaken for "nothing happened".
        from phonnect import control

        endpoint = control.read_endpoint()
        if endpoint is not None:
            try:
                control.request(*endpoint, {"cmd": "show"}, timeout=3)
            except OSError:
                pass
        return 0
    with lock:
        setup_logging(to_file=True, to_console=True)
        try:
            cfg = Config.load()
            adb, scrcpy, version, problem = resolve_tools(cfg)
            if problem:
                log.error(problem)
            from phonnect.tray import run_tray

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
        if (pid := running_pid()) is not None and pid > 0:
            print(f"Started (pid {pid}). Look for the phone icon in the tray / menu bar.")
            return 0
    print(f"The tray app did not start. Check the log: {paths.log_file()}")
    return 1


def cmd_stop(args) -> int:
    pid = running_pid()
    if pid is None:
        print("Not running.")
        return 0
    # Ask the app to quit, so it can put back what it changed on the phones first.
    from phonnect import control

    endpoint = control.read_endpoint()
    if endpoint is not None:
        try:
            if control.request(*endpoint, {"cmd": "quit"}, timeout=3).get("ok"):
                for _ in range(100):
                    if running_pid() is None:
                        print(f"Stopped (pid {pid}). Open scrcpy windows stay open.")
                        return 0
                    time.sleep(0.1)
        except OSError:
            pass
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
    print(f"scrcpy:         {scrcpy or 'NOT FOUND'}{f'  (v{version[0]}.{version[1]})' if version else ''}")
    print(f"adb:            {adb or 'NOT FOUND'}")
    print(f"config:         {paths.config_file()}")
    print(f"log:            {paths.log_file()}")
    return 1 if problem else 0


def cmd_doctor(args) -> int:
    ok = True
    print(f"Phonnect {__version__}, Python {sys.version.split()[0]} ({sys.executable})")
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
        elif d.online and d.transport == WIRELESS and Adb(adb).usb_debugging_enabled(d.serial) is False:
            print("  -> USB debugging is OFF on this phone: plugging it in won't be detected.")
            print("     Turn it on: Settings > System > Developer options > USB debugging")

    if (legacy := legacy_startup_entry()) is not None:
        print(f"warning: the old PowerShell watcher is still set to start at login: {legacy}")
        print("  It would open a second scrcpy window. Remove it: see docs/installation.md, migrating.")
    return 0 if ok else 1


def stop_legacy_app() -> bool:
    """Ask a still-running scrcpy-autolaunch (the app's old name) to quit, so it frees its folder."""
    from phonnect import control
    from phonnect.sidebar import process_alive

    old = paths.state_dir(paths.LEGACY_APP)
    try:
        pid = int((old / "instance.pid").read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return False
    if not process_alive(pid):
        return False  # stale pid file
    endpoint = control.parse_env((old / "control").read_text(encoding="ascii") if (old / "control").exists() else None)
    if endpoint is not None:
        try:
            control.request(*endpoint, {"cmd": "quit"}, timeout=3)
        except OSError:
            pass
    for _ in range(50):
        if not process_alive(pid):
            return True
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    return True


def cmd_install(args) -> int:
    # Coming from the old name (scrcpy-autolaunch): stop it, move its data, drop its entries.
    if stop_legacy_app():
        print("Stopped the old scrcpy-autolaunch app.")
    for line in paths.migrate_from_legacy():
        print(f"Settings: {line}")
    for p in autostart.remove_legacy_entries():
        print(f"Removed old entry: {p}")
    path = autostart.enable()
    print(f"Start at login enabled: {path}")
    menu = autostart.add_menu_entry()
    print(f"App menu entry: {menu}")
    if (legacy := legacy_startup_entry()) is not None:
        print(f"warning: old PowerShell watcher found in Startup: {legacy} (see docs/installation.md, migrating)")
    if shutil.which("scrcpy-autolaunch"):
        print(
            "Note: the old scrcpy-autolaunch command is still installed. "
            "Remove it with: uv tool uninstall scrcpy-autolaunch"
        )
    if args.no_start:
        return 0
    return cmd_start(args)


def cmd_update(args) -> int:
    from phonnect import updates

    releases = updates.check(force=True)
    if releases.phonnect is None:
        print("Could not reach GitHub to check for updates.")
        return 1
    version = updates.phonnect_update(releases)
    if version is None:
        print(f"Phonnect {__version__} is up to date (latest release: {releases.phonnect}).")
        return 0
    print(f"Phonnect {version} is available (installed: {__version__}).")
    if args.check:
        return 0
    if IS_WINDOWS:
        # This command's own files are about to be replaced, which Windows doesn't allow
        # while they run: the update continues in a new window.
        updates.start_update(version)
        print("The update continues in a new window.")
        return 0
    cmd = updates.updater_command(version)
    os.execvp(cmd[0], cmd)


def cmd_uninstall(args) -> int:
    cmd_stop(args)
    if autostart.disable():
        print(f"Removed start-at-login entry: {autostart.entry_path()}")
    if autostart.remove_menu_entry():
        print(f"Removed app menu entry: {autostart.menu_entry_path()}")
    for p in autostart.remove_legacy_entries():
        print(f"Removed old entry: {p}")
    if args.purge:
        dirs = {
            paths.config_dir(),
            paths.state_dir(),
            paths.config_dir(paths.LEGACY_APP),
            paths.state_dir(paths.LEGACY_APP),
        }
        for d in dirs:
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
    if args.qr:
        return _pair_with_qr(adb)
    if not args.address:
        return _dialog(adb, "pair")
    code = args.code or input("Pairing code: ").strip()
    ok, out = adb.pair(args.address, code)
    print(out)
    return 0 if ok else 1


def _pair_with_qr(adb: Adb) -> int:
    import segno

    from phonnect.wireless import KnownDevices, new_qr_pairing, pair_and_connect, wait_for_qr_scan

    pairing = new_qr_pairing()
    print("On the phone: Settings > System > Developer options > Wireless debugging > Pair device with QR code,")
    print("then scan this code (the phone and this computer must be on the same network):\n")
    segno.make(pairing.text, error="m").terminal(compact=True)
    print("\nWaiting for the phone (Ctrl+C to cancel) ...")
    try:
        address = wait_for_qr_scan(adb, pairing, lambda: False)
    except KeyboardInterrupt:
        return 130
    if address is None:
        print("The phone didn't show up within 5 minutes. Check that it's on the same network, then try again.")
        return 1
    ok, message = pair_and_connect(adb, KnownDevices(), address, pairing.password, progress=print)
    print(message)
    return 0 if ok else 1


def cmd_connect(args) -> int:
    adb = require_adb(Config.load())
    if not args.address:
        return _dialog(adb, "devices")
    from phonnect.wireless import KnownDevices, connect_verified, drop_offline, split_address

    if split_address(args.address):
        drop_offline(adb, split_address(args.address)[0])
    ok, out = connect_verified(adb, args.address)
    print(out)
    if ok:
        KnownDevices().remember(adb.hardware_id(args.address), address=args.address)
    return 0 if ok else 1


def cmd_wifi(args) -> int:
    """List remembered/paired phones, or reconnect to one."""
    from phonnect.wireless import KnownDevices, reconnect, status_of

    adb = require_adb(Config.load())
    known = KnownDevices()
    devices = known.all()
    if not args.reconnect:
        current = adb.devices()
        if not devices:
            print("No paired or remembered phones. Pair one with: phonnect pair")
        for d in devices:
            print(
                f"{d.label:20} {status_of(d, current):16} last={d.address or '-':22} ip={d.ip or '-':16} id={d.hw_id}"
            )
        return 0
    wanted = args.reconnect.lower()
    matches = [d for d in devices if wanted in (d.hw_id.lower(), d.label.lower()) or wanted == "all"]
    if not matches:
        print(f"No remembered phone matches '{args.reconnect}'.")
        return 1
    rc = 0
    for d in matches:
        ok, result = reconnect(adb, d, progress=print)
        print(f"{d.label}: {'connected at ' + result if ok else 'failed'}")
        if ok:
            known.remember(d.hw_id, address=result)
        else:
            print(result)
            rc = 1
    return rc


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
    return _dialog(require_adb(Config.load()), args.kind, args.message)


def cmd_mirror(args) -> int:
    """Ask the running tray app to open a mirror window."""
    from phonnect import control

    endpoint = control.read_endpoint()
    if endpoint is None or running_pid() is None:
        print("Phonnect isn't running. Start it with: phonnect start")
        return 1
    try:
        reply = control.request(*endpoint, {"cmd": "mirror", "phone": args.phone})
    except OSError as exc:
        print(f"Could not reach the running app: {exc}")
        return 1
    if not reply.get("ok"):
        print(reply.get("error", "failed"))
        return 1
    print(reply.get("result") or f"started {reply.get('started', 0)} window(s)")
    return 0


def cmd_sidebar(args) -> int:
    from phonnect.sidebar import run_sidebar

    adb = os.environ.get("ADB") or require_adb(Config.load()).path
    return run_sidebar(adb, args.serial, args.hw, args.pid, args.name)


def _dialog(adb: Adb, kind: str, message: str = "") -> int:
    from phonnect.dialogs import run_dialog

    code = run_dialog(kind, adb, message)
    if code == 3 and sys.stderr is not None:
        print("Tk is not available; pass the address on the command line instead.", file=sys.stderr)
    return code


# ── entry points ─────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="phonnect",
        description="Phonnect: your phone on your desktop, as soon as you plug it in or come near (built on scrcpy).",
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
    add("mirror", cmd_mirror, "open a mirror window (asks the running app)").add_argument(
        "phone", nargs="?", default="all", help="phone name, serial or 'all' (default)"
    )
    sp = add("pair", cmd_pair, "pair a phone for wireless debugging (opens a dialog without arguments)")
    sp.add_argument("address", nargs="?", help="IP:PORT from 'Pair device with pairing code'")
    sp.add_argument("code", nargs="?", help="6-digit pairing code")
    sp.add_argument("--qr", action="store_true", help="show a QR code to scan with the phone instead")
    add(
        "connect", cmd_connect, "connect over Wi-Fi to IP:PORT (opens the Wi-Fi devices window without arguments)"
    ).add_argument("address", nargs="?", help="IP:PORT shown on the Wireless debugging screen")
    add("wifi", cmd_wifi, "list paired / remembered phones, or reconnect to one").add_argument(
        "--reconnect", metavar="NAME|ID|all", help="reconnect (tries mDNS, last address, then a port scan)"
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
    add("update", cmd_update, "check for a new release and install it").add_argument(
        "--check", action="store_true", help="only check, don't install"
    )
    sp = add("_dialog", cmd_dialog, argparse.SUPPRESS)
    sp.add_argument("kind", choices=["pair", "connect", "devices"])
    sp.add_argument("--message", default="")
    sp = add("_sidebar", cmd_sidebar, argparse.SUPPRESS)
    sp.add_argument("--serial", required=True)
    sp.add_argument("--hw", required=True)
    sp.add_argument("--pid", type=int, required=True)
    sp.add_argument("--name", default="Phone")
    # Hide the internal commands from --help.
    sub._choices_actions = [a for a in sub._choices_actions if not a.dest.startswith("_")]
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        sys.exit(0)
    if args.command in ("run", "tray", "start", "status", "doctor"):
        paths.migrate_from_legacy()  # no-op unless upgrading from scrcpy-autolaunch
    sys.exit(args.func(args))


def tray_main() -> None:
    """Entry point of the windowless `phonnect-tray` executable."""
    paths.migrate_from_legacy()
    sys.exit(cmd_tray(None))
