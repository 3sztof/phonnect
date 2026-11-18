import json

from scrcpy_autolaunch.config import Config


def test_defaults_keep_audio_on_phone(tmp_path):
    cfg = Config.load(tmp_path / "missing.json")
    assert cfg.auto_usb is True
    assert cfg.auto_wireless is False
    assert cfg.audio == "off"


def test_roundtrip(tmp_path):
    path = tmp_path / "sub" / "config.json"
    cfg = Config(auto_wireless=True, scrcpy_args=["--stay-awake"], audio="both")
    cfg.save(path)
    assert Config.load(path) == cfg


def test_unknown_keys_ignored_and_missing_defaulted(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"auto_usb": False, "from_the_future": 1}))
    cfg = Config.load(path)
    assert cfg.auto_usb is False
    assert cfg.poll_interval == 1.0


def test_broken_file_gives_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json")
    assert Config.load(path) == Config()
