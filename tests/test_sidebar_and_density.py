import json
import os

import pytest

from scrcpy_autolaunch import control
from scrcpy_autolaunch.adb import parse_wm_density
from scrcpy_autolaunch.osutil import linux_terminal_command
from scrcpy_autolaunch.phone_state import DensityKeeper
from scrcpy_autolaunch.sidebar import dock_position, process_alive
from test_watcher import USB_PHONE, Harness

HW = USB_PHONE.serial


class DensityAdb:
    def __init__(self, physical=360, override=400):
        self.state = {"physical": physical, "override": override}
        self.writes = []

    def density_state(self, serial):
        return dict(self.state)

    def apply_density(self, serial, state):
        self.writes.append(state.get("override"))
        self.state = {"physical": self.state["physical"], "override": state.get("override")}
        return True


def keeper(tmp_path, adb):
    return DensityKeeper(adb, lambda hw: HW, path=tmp_path / "density.json", threaded=False)


# ── density ──────────────────────────────────────────────────────────────────


def test_parse_wm_density():
    assert parse_wm_density("Physical density: 360\nOverride density: 400\n") == {"physical": 360, "override": 400}
    assert parse_wm_density("Physical density: 420\n") == {"physical": 420, "override": None}
    assert parse_wm_density("error") is None


def test_scale_is_relative_to_the_users_own_setting_and_restores_it(tmp_path):
    adb = DensityAdb(physical=360, override=400)  # user already set a custom display size
    k = keeper(tmp_path, adb)
    k.set_scale(HW, 75)
    assert adb.state["override"] == 300
    k.set_scale(HW, 50)
    assert adb.state["override"] == 200, "still relative to the original 400, not to 300"
    k.restore(HW)
    assert adb.state == {"physical": 360, "override": 400}


def test_default_density_is_reset_not_pinned(tmp_path):
    adb = DensityAdb(physical=420, override=None)
    k = keeper(tmp_path, adb)
    k.set_scale(HW, 80)
    k.set_scale(HW, 100)  # back to 100% = restore
    assert adb.writes == [336, None]
    assert not k.has_saved(HW)


def test_scale_is_clamped(tmp_path):
    adb = DensityAdb(physical=400, override=None)
    keeper(tmp_path, adb).set_scale(HW, 5)
    assert adb.state["override"] == 200


# ── watcher integration ──────────────────────────────────────────────────────


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRCPY_AUTOLAUNCH_HOME", str(tmp_path))
    return tmp_path


def test_watcher_applies_content_scale_on_launch_and_restores_on_close(home):
    h = Harness(content_scale=75)
    adb = DensityAdb()
    h.watcher.density = DensityKeeper(adb, h.watcher.online_serial, path=home / "d.json", threaded=False)
    h.tick(USB_PHONE)
    assert adb.state["override"] == 300
    h.now += 60
    h.procs[0].close_window()
    h.tick(USB_PHONE)
    assert adb.state["override"] == 400


def test_control_requests_change_settings(home):
    h = Harness()
    adb = DensityAdb()
    h.watcher.density = DensityKeeper(adb, h.watcher.online_serial, path=home / "d.json", threaded=False)
    h.tick(USB_PHONE)
    assert h.watcher.handle_control({"cmd": "state"})["content_scale"] == 100
    assert h.watcher.handle_control({"cmd": "set_scale", "value": 60})["content_scale"] == 60
    assert adb.state["override"] == 240
    assert json.loads((home / "config.json").read_text())["content_scale"] == 60
    assert h.watcher.handle_control({"cmd": "set_scale", "value": "x"})["ok"] is False
    assert h.watcher.handle_control({"cmd": "set_landscape", "on": True})["ok"]
    assert h.watcher.config.force_landscape is True
    assert h.watcher.handle_control({"cmd": "nope"})["ok"] is False


def test_no_sidebar_without_control_server():
    h = Harness()
    h.tick(USB_PHONE)
    assert h.watcher.sessions[HW].sidebar is None


# ── control channel ──────────────────────────────────────────────────────────


def test_control_server_roundtrip_and_token():
    server = control.ControlServer(lambda msg: {"ok": True, "echo": msg["cmd"]}).start()
    try:
        assert control.request(server.address, server.token, {"cmd": "ping"}) == {"ok": True, "echo": "ping"}
        assert control.request(server.address, "wrong", {"cmd": "ping"})["error"] == "unauthorized"
        assert server.address.startswith("127.0.0.1:")
    finally:
        server.stop()
    assert control.parse_env(f"{server.address} {server.token}") == (server.address, server.token)
    assert control.parse_env(None) is None


# ── sidebar helpers ──────────────────────────────────────────────────────────


def test_dock_position_right_then_left_at_screen_edge():
    screen = (0, 0, 1920, 1080)
    assert dock_position((100, 50, 600, 950), 52, screen) == (600, 50, 52, 900)
    assert dock_position((1400, 50, 1900, 950), 52, screen) == (1348, 50, 52, 900)


def test_process_alive():
    assert process_alive(os.getpid())


def test_linux_terminal_choice():
    available = {"konsole", "xterm"}
    which = lambda name: name if name in available else None  # noqa: E731
    assert linux_terminal_command(["adb", "shell"], which=which, env={}) == ["konsole", "-e", "adb", "shell"]
    assert linux_terminal_command(["adb"], which=which, env={"TERMINAL": "xterm"}) == ["xterm", "-e", "adb"]
    assert linux_terminal_command(["adb"], which=lambda n: None, env={}) is None


def test_wifi_close_restores_density_before_disconnecting(home):
    from test_watcher import WIFI_OTHER_PHONE, _wait_for

    order = []
    h = Harness(auto_wireless=True, content_scale=50)
    adb = DensityAdb()
    real_apply = adb.apply_density

    def apply(serial, state):
        order.append(("density", state.get("override")))
        return real_apply(serial, state)

    adb.apply_density = apply
    h.adb.disconnect = lambda serial=None: order.append(("disconnect", serial))
    h.watcher.density = DensityKeeper(adb, h.watcher.online_serial, path=home / "d.json")  # threaded, like the app
    h.tick(WIFI_OTHER_PHONE)
    h.now += 60
    h.procs[0].close_window(code=0)
    h.tick(WIFI_OTHER_PHONE)
    assert _wait_for(lambda: len(order) == 3)
    assert order == [("density", 200), ("density", 400), ("disconnect", WIFI_OTHER_PHONE.serial)]


def test_mirror_and_quit_requests(home):
    h = Harness(auto_usb=False)
    h.tick(USB_PHONE)
    assert h.watcher.handle_control({"cmd": "mirror", "phone": "pixel 9 pro"}) == {"ok": True, "result": "started"}
    assert h.watcher.handle_control({"cmd": "mirror", "phone": "nope"})["ok"] is False
    assert h.watcher.handle_control({"cmd": "quit"})["ok"] is False, "no quit handler set"
    quit_called = []
    h.watcher.on_quit = lambda: quit_called.append(True)
    assert h.watcher.handle_control({"cmd": "quit"})["ok"]
    from test_watcher import _wait_for

    assert _wait_for(lambda: quit_called)


def test_desktop_mode_opens_second_window_once():
    h = Harness(auto_usb=False)
    h.tick(USB_PHONE)
    assert h.watcher.open_desktop(HW) == "started"
    args = h.procs[0].args
    assert "--new-display=1920x1080/160" in args and "--no-audio" in args
    assert "--window-title=Pixel 9 Pro desktop" in args
    assert h.watcher.open_desktop(HW) == "already open"
    assert len(h.procs) == 1
    h.procs[0].close_window()
    h.tick(USB_PHONE)
    assert h.watcher.open_desktop(HW) == "started"


def test_desktop_mode_needs_connection_and_scrcpy_3():
    h = Harness()
    assert h.watcher.open_desktop("missing") == "not connected"
    h.tick(USB_PHONE)
    h.watcher.scrcpy_version = (2, 7)
    assert h.watcher.open_desktop(HW) == "desktop mode needs scrcpy 3.0 or newer"


def test_desktop_request_from_sidebar():
    h = Harness(auto_usb=False)
    h.tick(USB_PHONE)
    assert h.watcher.handle_control({"cmd": "open_desktop", "hw": HW}) == {"ok": True, "result": "started"}
