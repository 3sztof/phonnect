from scrcpy_autolaunch.adb import Device
from scrcpy_autolaunch.config import Config
from scrcpy_autolaunch.watcher import Watcher

USB_PHONE = Device("1A2B3C4D5E6F7G", "device", "Pixel_9_Pro")
WIFI_SAME_PHONE = Device("adb-1A2B3C4D5E6F7G-x._adb-tls-connect._tcp", "device", "Pixel_9_Pro")
WIFI_OTHER_PHONE = Device("192.168.1.30:5555", "device", "Pixel_7")


class FakeAdb:
    path = "adb"

    def __init__(self):
        self.current: list[Device] = []
        self.hw = {WIFI_SAME_PHONE.serial: USB_PHONE.serial}

    def start_server(self):
        pass

    def devices(self):
        return list(self.current)

    def hardware_id(self, serial):
        return self.hw.get(serial, serial)


class FakeProc:
    _next_pid = 100

    def __init__(self, args):
        self.args = args
        self.returncode = None
        self.stdout = None
        FakeProc._next_pid += 1
        self.pid = FakeProc._next_pid

    def poll(self):
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
        "scrcpy", "-s", USB_PHONE.serial, "--no-audio", "--stay-awake", "--keyboard=uhid"
    ]


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
    assert h.procs[0].args[-3:] == ["--max-size=1600", "--video-bit-rate=6M", "--keyboard=uhid"]


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
