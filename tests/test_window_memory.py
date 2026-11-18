from phonnect.window_memory import WindowMemory, fitted_width


def test_remembers_per_orientation_and_reopens_with_height_only(tmp_path):
    m = WindowMemory(tmp_path / "windows.json")
    assert m.remember("HW", 100, 50, 450, 1000)  # portrait
    assert m.remember("HW", 30, 40, 1600, 720)  # landscape
    assert not m.remember("HW", 100, 50, 450, 1000), "unchanged: nothing to save"
    on_screen = lambda x, y: True
    # Only the height goes to scrcpy: it works out the width from the picture, so no black bars.
    assert m.launch_args("HW", landscape=False, on_screen=on_screen) == [
        "--window-height=1000",
        "--window-x=100",
        "--window-y=50",
    ]
    assert m.launch_args("HW", landscape=True, on_screen=on_screen)[0] == "--window-height=720"
    # Saved to disk.
    assert WindowMemory(tmp_path / "windows.json").get("HW", landscape=False) == {"x": 100, "y": 50, "height": 1000}


def test_nothing_saved_means_scrcpys_default(tmp_path):
    assert WindowMemory(tmp_path / "w.json").launch_args("HW", landscape=False) == []


def test_off_screen_position_is_dropped_but_size_kept(tmp_path):
    m = WindowMemory(tmp_path / "w.json")
    m.remember("HW", 5000, 50, 450, 1000)  # on a monitor that's gone now
    assert m.launch_args("HW", landscape=False, on_screen=lambda x, y: False) == ["--window-height=1000"]


def test_tiny_windows_are_not_remembered(tmp_path):
    m = WindowMemory(tmp_path / "w.json")
    assert not m.remember("HW", 0, 0, 80, 120)
    assert m.launch_args("HW", landscape=False) == []


def test_desktop_window_has_its_own_entry(tmp_path):
    m = WindowMemory(tmp_path / "w.json")
    m.remember(m.key("HW", desktop=True), 10, 10, 1600, 900)
    assert m.get("HW", landscape=True) is None
    assert m.get(m.key("HW", desktop=True), landscape=True)["height"] == 900


def test_fitted_width_removes_black_bars():
    # The window seen on a 3440x1440 screen: 618x1360 for a 720x1600 picture.
    assert fitted_width(618, 1360, 720, 1600) == 612
    assert fitted_width(612, 1360, 720, 1600) is None, "already fits"
    assert fitted_width(0, 1360, 720, 1600) is None


def test_mirror_reopens_where_it_was(tmp_path):
    from phonnect.adb import Device
    from phonnect.config import Config
    from phonnect.watcher import Watcher

    w = Watcher(Config(), adb=None, scrcpy="scrcpy", scrcpy_version=(3, 3))
    dev = Device("1A2B3C4D5E6F7G", "device", "Pixel_9_Pro")
    assert not any(a.startswith("--window") for a in w.build_args(dev)), "off: scrcpy's default"
    w.windows = WindowMemory(tmp_path / "w.json")
    w.windows.remember("1A2B3C4D5E6F7G", 100, 50, 450, 1000)
    args = w.build_args(dev)
    assert "--window-height=1000" in args
    # The user's own scrcpy_args win.
    w.config.scrcpy_args = ["--window-height=800"]
    assert [a for a in w.build_args(dev) if a.startswith("--window")] == ["--window-height=800"]
