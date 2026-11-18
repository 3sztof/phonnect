from PIL import Image

from phonnect import icons


def test_icon_files_written(tmp_path, monkeypatch):
    monkeypatch.setenv("PHONNECT_HOME", str(tmp_path))
    ico, png = icons.ensure_icon_files()
    assert Image.open(png).size == (256, 256)
    assert (16, 16) in Image.open(ico).info["sizes"]


def test_tray_states_differ():
    imgs = {s: icons.tray_icon(s).tobytes() for s in ("waiting", "connected", "problem")}
    assert len(set(imgs.values())) == 3
