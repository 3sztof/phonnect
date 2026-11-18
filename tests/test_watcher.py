from scrcpy_autolaunch.adb import Device
from scrcpy_autolaunch.config import Config
from scrcpy_autolaunch.watcher import Watcher

USB_PHONE = Device("1A2B3C4D5E6F7G", "device", "Pixel_9_Pro")
WIFI_SAME_PHONE = Device("adb-1A2B3C4D5E6F7G-x._adb-tls-connect._tcp", "device", "Pixel_9_Pro")
WIFI_OTHER_PHONE = Device("192.168.1.30:5555", "device", "Pixel_7")


class FakeAdb:
    path = "adb"

    def __init__(self):
        self.disconnected = []
        self.current: list[Device] = []
        self.hw = {WIFI_SAME_PHONE.serial: USB_PHONE.serial}

    def start_server(self):
        pass

    def devices(self):
        return list(self.current)

    def hardware_id(self, serial):
        return self.hw.get(serial, serial)

    disconnected: list

    def disconnect(self, serial=None):
        self.disconnected.append(serial)
        return "disconnected"


class FakeProc:
    _next_pid = 100

    def __init__(self, args):
        self.args = args
        self.returncode = None
        self.stdout = None
        self.terminated = False
        FakeProc._next_pid += 1
        self.pid = FakeProc._next_pid

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 1

    def kill(self):
        self.terminate()

    def wait(self, timeout=None):
        return self.returncode

    def close_window(self, code=0):
        self.returncode = code


class Harness:
    def __init__(self, **cfg):
        self.adb = FakeAdb()
        self.procs: list[FakeProc] = []
        self.notes: list[str] = []
        self.now = 0.0
        self.watcher = Watcher(
            Config(**cfg),
            self.adb,
            "scrcpy",
            (3, 3),
            notify=self.notes.append,
            popen=self._popen,
            clock=lambda: self.now,
        )

    def _popen(self, args, **kwargs):
        proc = FakeProc(args)
        self.procs.append(proc)
        return proc

    def tick(self, *devices):
        self.adb.current = list(devices)
        self.now += 1
        self.watcher.tick()


def test_launches_on_usb_connect():
    h = Harness()
    h.tick(USB_PHONE)
    assert len(h.procs) == 1
    assert h.procs[0].args == [
        "scrcpy", "-s", USB_PHONE.serial, "--stay-awake", "--no-audio", "--keyboard=uhid"
    ]


def test_audio_modes():
    h = Harness()
    audio = lambda: [a for a in h.watcher.build_args(USB_PHONE) if "audio" in a]  # noqa: E731
    assert audio() == ["--no-audio"]
    h.watcher.config.audio = "both"
    assert audio() == ["--audio-source=playback", "--audio-dup"]
    h.watcher.config.audio = "pc"
    assert audio() == []
    h.watcher.scrcpy_version = (2, 5)
    h.watcher.config.audio = "both"
    assert audio() == ["--no-audio"], "too old for --audio-dup: keep sound on the phone"


def test_legacy_no_audio_in_scrcpy_args_does_not_override_audio_mode():
    h = Harness(scrcpy_args=["--no-audio", "--stay-awake"], audio="both")
    args = h.watcher.build_args(USB_PHONE)
    assert "--no-audio" not in args and "--audio-dup" in args


def test_restart_sessions_relaunches_with_new_settings():
    h = Harness()
    h.tick(USB_PHONE)
    h.watcher.config.audio = "both"
    assert h.watcher.restart_sessions() == 1
    assert h.procs[0].terminated
    assert "--audio-dup" in h.procs[1].args
    h.tick(USB_PHONE)
    assert h.notes == [], "a restart must not be reported as a failure"


def test_keyboard_toggle_and_user_override():
    h = Harness(hide_phone_keyboard=False)
    assert not any(a.startswith("--keyboard") for a in h.watcher.build_args(USB_PHONE))
    h = Harness(scrcpy_args=["--no-audio", "--keyboard=sdk"])
    assert [a for a in h.watcher.build_args(USB_PHONE) if a.startswith("--keyboard")] == ["--keyboard=sdk"]
    h = Harness()
    h.watcher.scrcpy_version = (2, 3)
    assert "--keyboard=uhid" not in h.watcher.build_args(USB_PHONE)


def test_closing_window_does_not_relaunch_until_replug():
    h = Harness()
    h.tick(USB_PHONE)
    h.now += 60
    h.procs[0].close_window()
    for _ in range(5):
        h.tick(USB_PHONE)
    assert len(h.procs) == 1, "must not relaunch while still plugged in"
    h.tick()  # unplugged
    h.tick(USB_PHONE)  # replugged
    assert len(h.procs) == 2


def test_no_launch_when_auto_usb_off_but_mirror_now_works():
    h = Harness(auto_usb=False)
    h.tick(USB_PHONE)
    assert h.procs == []
    assert h.watcher.mirror_now() == 1
    assert len(h.procs) == 1


def test_wireless_off_by_default_and_gets_extra_args_when_on():
    h = Harness()
    h.tick(WIFI_OTHER_PHONE)
    assert h.procs == []
    h = Harness(auto_wireless=True)
    h.tick(WIFI_OTHER_PHONE)
    assert h.procs[0].args[-4:] == ["--max-size=1600", "--video-bit-rate=6M", "--no-audio", "--keyboard=uhid"]


def test_same_phone_on_usb_and_wifi_gets_one_window_via_usb():
    h = Harness(auto_wireless=True)
    h.tick(WIFI_SAME_PHONE, USB_PHONE)
    assert len(h.procs) == 1
    assert h.procs[0].args[2] == USB_PHONE.serial
    assert h.watcher.mirror_now() == 0


def test_unauthorized_then_authorized_launches_once():
    h = Harness()
    h.tick(Device(USB_PHONE.serial, "unauthorized"))
    assert h.procs == []
    h.tick(USB_PHONE)
    h.tick(USB_PHONE)
    assert len(h.procs) == 1


def test_quick_failure_notifies():
    h = Harness()
    h.tick(USB_PHONE)
    h.procs[0].close_window(code=1)
    h.tick(USB_PHONE)
    assert h.notes and "exit code 1" in h.notes[0]


def test_normal_close_does_not_notify():
    h = Harness()
    h.tick(USB_PHONE)
    h.now += 60
    h.procs[0].close_window(code=0)
    h.tick(USB_PHONE)
    assert h.notes == []


def test_old_scrcpy_drops_audio_flags():
    h = Harness()
    h.watcher.scrcpy_version = (1, 25)
    assert "--no-audio" not in h.watcher.build_args(USB_PHONE)


def test_snapshot_reports_mirroring():
    h = Harness()
    h.tick(USB_PHONE)
    assert h.watcher.snapshot() == [(USB_PHONE, True)]
    h.now += 60
    h.procs[0].close_window()
    h.tick(USB_PHONE)
    assert h.watcher.snapshot() == [(USB_PHONE, False)]


def test_per_phone_mirror_stop_and_phones():
    h = Harness(auto_usb=False)
    h.tick(USB_PHONE)
    assert h.watcher.phones() == [(USB_PHONE.serial, [USB_PHONE], False)]
    assert h.watcher.mirror("unknown") == "not connected"
    assert h.watcher.mirror(USB_PHONE.serial) == "started"
    assert h.watcher.mirror(USB_PHONE.serial) == "already mirroring"
    assert h.watcher.session_pid(USB_PHONE.serial) == h.procs[0].pid
    assert h.watcher.stop_mirroring(USB_PHONE.serial)
    h.tick(USB_PHONE)
    assert h.notes == [], "stopping from the tray is not a failure"
    assert h.watcher.phones()[0][2] is False


def test_explicit_mirror_works_over_wifi_with_auto_wireless_off():
    h = Harness()
    h.tick(WIFI_OTHER_PHONE)
    assert h.procs == []
    assert h.watcher.mirror(WIFI_OTHER_PHONE.serial) == "started"


class FakeKnown:
    def __init__(self):
        self.calls = []

    def remember(self, hw, **kw):
        self.calls.append((hw, kw))


def test_warns_once_when_usb_debugging_is_off():
    h = Harness()
    h.adb.wifi_ip = lambda s: "192.168.1.132"
    h.adb.tls_port = lambda s: 0
    h.adb.wifi_debugging_enabled = lambda s: True
    h.adb.usb_debugging_enabled = lambda s: False
    h.watcher.known = FakeKnown()
    h.watcher._learn(WIFI_SAME_PHONE, USB_PHONE.serial)
    h.watcher._learn(WIFI_SAME_PHONE, USB_PHONE.serial)
    assert len(h.notes) == 1 and "USB debugging is off" in h.notes[0]


def _wait_for(cond, timeout=2.0):
    import time

    end = time.monotonic() + timeout
    while time.monotonic() < end and not cond():
        time.sleep(0.01)
    return cond()


def test_closing_wifi_window_disconnects_by_default():
    h = Harness(auto_wireless=True)
    h.tick(WIFI_OTHER_PHONE)
    h.now += 60
    h.procs[0].close_window(code=0)
    h.tick(WIFI_OTHER_PHONE)
    assert _wait_for(lambda: h.adb.disconnected == [WIFI_OTHER_PHONE.serial])


def test_keep_wifi_connected_option():
    h = Harness(auto_wireless=True, keep_wifi_connected=True)
    h.tick(WIFI_OTHER_PHONE)
    h.now += 60
    h.procs[0].close_window(code=0)
    h.tick(WIFI_OTHER_PHONE)
    assert not _wait_for(lambda: h.adb.disconnected, timeout=0.2)


def test_usb_close_and_crashes_do_not_disconnect():
    h = Harness(auto_wireless=True)
    h.tick(USB_PHONE, WIFI_OTHER_PHONE)
    h.now += 60
    h.procs[0].close_window(code=0)  # USB window closed by the user
    h.procs[1].close_window(code=2)  # Wi-Fi window lost its connection
    h.tick(USB_PHONE, WIFI_OTHER_PHONE)
    assert not _wait_for(lambda: h.adb.disconnected, timeout=0.2)


def test_wifi_reconnect_after_user_close_does_not_reopen_until_clicked():
    h = Harness(auto_wireless=True, keep_wifi_connected=True)
    h.tick(WIFI_OTHER_PHONE)
    h.now += 60
    h.procs[0].close_window(code=0)
    h.tick(WIFI_OTHER_PHONE)
    h.tick()  # drops off Wi-Fi
    h.tick(WIFI_OTHER_PHONE)  # adb reconnects it by itself (mDNS)
    assert len(h.procs) == 1
    assert h.watcher.mirror(WIFI_OTHER_PHONE.serial) == "started"


def test_stop_mirroring_from_tray_disconnects_wifi():
    h = Harness(auto_wireless=True)
    h.tick(WIFI_OTHER_PHONE)
    h.watcher.stop_mirroring(WIFI_OTHER_PHONE.serial)
    assert _wait_for(lambda: h.adb.disconnected == [WIFI_OTHER_PHONE.serial])
