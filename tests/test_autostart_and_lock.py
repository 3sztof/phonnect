import plistlib

from phonnect import autostart
from phonnect.instance import InstanceLock


def test_linux_desktop_entry_quotes_paths_with_spaces():
    entry = autostart.linux_desktop_entry(["/home/a b/.local/bin/phonnect-tray"])
    assert 'Exec="/home/a b/.local/bin/phonnect-tray"' in entry
    assert "Terminal=false" in entry


def test_linux_desktop_entry_plain_path_unquoted():
    entry = autostart.linux_desktop_entry(["/usr/bin/python3", "-m", "phonnect", "tray"])
    assert "Exec=/usr/bin/python3 -m phonnect tray" in entry


def test_macos_plist():
    data = plistlib.loads(autostart.macos_plist(["/Users/x/.local/bin/phonnect-tray"]))
    assert data["ProgramArguments"] == ["/Users/x/.local/bin/phonnect-tray"]
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
    entry = autostart.linux_desktop_entry(["/x/phonnect-tray"], autostart=False)
    assert "Categories=Utility;" in entry
    assert "X-GNOME-Autostart-enabled" not in entry


def test_mac_app_bundle_starts_the_tray_without_a_dock_icon(tmp_path):
    app = tmp_path / "Phonnect.app"
    autostart.write_mac_app(app, ["/Users/a b/.local/bin/phonnect-tray"])
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    assert info["CFBundleExecutable"] == "Phonnect" and info["LSUIElement"] is True
    launcher = (app / "Contents" / "MacOS" / "Phonnect").read_text()
    assert launcher.startswith("#!/bin/sh\nexec '/Users/a b/.local/bin/phonnect-tray'")
    assert (app / "Contents" / "Resources" / "Phonnect.icns").stat().st_size > 1000


def test_entries_are_refreshed_once_per_version(monkeypatch):
    calls = []
    monkeypatch.setattr(autostart, "is_enabled", lambda: True)
    monkeypatch.setattr(autostart, "enable", lambda: calls.append("login") or "login-entry")
    monkeypatch.setattr(autostart, "menu_entry_path", lambda: type("P", (), {"exists": lambda self: False})())
    assert autostart.refresh_entries("1.0.0") == ["login-entry"]
    assert autostart.refresh_entries("1.0.0") == []
    assert autostart.refresh_entries("1.1.0") == ["login-entry"]
    assert calls == ["login", "login"]


def test_windows_entries_are_capitalised():
    assert autostart.entry_path().name in ("Phonnect.lnk", "io.github.3sztof.phonnect.plist", "phonnect.desktop")
