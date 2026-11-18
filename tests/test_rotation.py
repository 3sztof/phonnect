from phonnect.adb import LANDSCAPE
from phonnect.phone_state import RotationKeeper
from test_watcher import USB_PHONE, Harness

HW = USB_PHONE.serial
PORTRAIT_AUTO = {"method": "wm", "mode": "free", "rotation": 0, "fixed": "default"}


class RotatingAdb:
    """Pretends to be a phone's rotation settings."""

    def __init__(self, state=None):
        self.state = dict(state or PORTRAIT_AUTO)
        self.reachable = True
        self.applied = []

    def rotation_state(self, serial):
        return dict(self.state) if self.reachable else None

    def apply_rotation(self, serial, state):
        if not self.reachable:
            return False
        self.applied.append(dict(state))
        self.state = dict(state)
        return True


def keeper(tmp_path, adb, online=True):
    return RotationKeeper(adb, lambda hw: HW if online else None, path=tmp_path / "rot.json", threaded=False)


def test_lock_then_restore_puts_back_original(tmp_path):
    adb = RotatingAdb()
    k = keeper(tmp_path, adb)
    k.lock_landscape(HW)
    assert adb.state == LANDSCAPE["wm"]
    k.lock_landscape(HW)  # second lock must not overwrite the saved original
    k.restore(HW)
    assert adb.state == PORTRAIT_AUTO
    assert not k.has_saved(HW)


def test_unreachable_phone_is_restored_after_restart(tmp_path):
    adb = RotatingAdb()
    keeper(tmp_path, adb).lock_landscape(HW)
    adb.reachable = False
    k2 = keeper(tmp_path, adb)  # e.g. the app restarted
    k2.restore(HW)
    assert k2.has_saved(HW), "kept on disk because the phone couldn't be reached"
    adb.reachable = True
    keeper(tmp_path, adb).restore(HW)
    assert adb.state == PORTRAIT_AUTO


def test_watcher_locks_on_launch_and_restores_on_close(tmp_path):
    h = Harness(force_landscape=True)
    adb = RotatingAdb()
    h.watcher.rotation = RotationKeeper(adb, h.watcher.online_serial, path=tmp_path / "rot.json", threaded=False)
    h.tick(USB_PHONE)
    assert adb.state == LANDSCAPE["wm"]
    h.now += 60
    h.procs[0].close_window()
    h.tick(USB_PHONE)
    assert adb.state == PORTRAIT_AUTO


def test_toggle_while_mirroring_and_off_by_default(tmp_path):
    h = Harness()
    adb = RotatingAdb()
    h.watcher.rotation = RotationKeeper(adb, h.watcher.online_serial, path=tmp_path / "rot.json", threaded=False)
    h.tick(USB_PHONE)
    assert adb.applied == [], "off by default"
    h.watcher.config.force_landscape = True
    h.watcher.apply_landscape_setting()
    assert adb.state == LANDSCAPE["wm"]
    h.watcher.config.force_landscape = False
    h.watcher.apply_landscape_setting()
    assert adb.state == PORTRAIT_AUTO


def test_restart_sessions_keeps_landscape_without_flipping(tmp_path):
    h = Harness(force_landscape=True)
    adb = RotatingAdb()
    h.watcher.rotation = RotationKeeper(adb, h.watcher.online_serial, path=tmp_path / "rot.json", threaded=False)
    h.tick(USB_PHONE)
    h.watcher.restart_sessions()
    assert PORTRAIT_AUTO not in adb.applied
