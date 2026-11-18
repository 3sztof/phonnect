import plistlib

from scrcpy_autolaunch import autostart
from scrcpy_autolaunch.instance import InstanceLock


def test_linux_desktop_entry_quotes_paths_with_spaces():
    entry = autostart.linux_desktop_entry(["/home/a b/.local/bin/scrcpy-autolaunch-tray"])
    assert 'Exec="/home/a b/.local/bin/scrcpy-autolaunch-tray"' in entry
    assert "Terminal=false" in entry


def test_linux_desktop_entry_plain_path_unquoted():
    entry = autostart.linux_desktop_entry(["/usr/bin/python3", "-m", "scrcpy_autolaunch", "tray"])
    assert "Exec=/usr/bin/python3 -m scrcpy_autolaunch tray" in entry


def test_macos_plist():
    data = plistlib.loads(autostart.macos_plist(["/Users/x/.local/bin/scrcpy-autolaunch-tray"]))
    assert data["ProgramArguments"] == ["/Users/x/.local/bin/scrcpy-autolaunch-tray"]
    assert data["RunAtLoad"] is True
    assert "/opt/homebrew/bin" in data["EnvironmentVariables"]["PATH"]


def test_instance_lock_is_exclusive(tmp_path):
    a = InstanceLock(tmp_path / "x.lock", tmp_path / "x.pid")
    b = InstanceLock(tmp_path / "x.lock", tmp_path / "x.pid")
    assert a.acquire()
    assert not b.acquire()
    a.release()
    assert b.acquire()
    b.release()


def test_linux_menu_entry_is_not_an_autostart_entry():
    entry = autostart.linux_desktop_entry(["/x/scrcpy-autolaunch-tray"], autostart=False)
    assert "Categories=Utility;" in entry
    assert "X-GNOME-Autostart-enabled" not in entry
