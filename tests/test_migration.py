from phonnect import paths


def _isolated(tmp_path, monkeypatch):
    monkeypatch.delenv("PHONNECT_HOME", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_migrates_old_folders_once(tmp_path, monkeypatch):
    _isolated(tmp_path, monkeypatch)
    old_cfg = paths.config_dir(paths.LEGACY_APP)
    old_state = paths.state_dir(paths.LEGACY_APP)
    old_cfg.mkdir(parents=True)
    old_state.mkdir(parents=True, exist_ok=True)
    (old_cfg / "config.json").write_text('{"audio": "pc"}')
    (old_state / "density.json").write_text('{"PHONE": {"physical": 360, "override": 400}}')
    (old_state / "scrcpy-autolaunch.log").write_text("old log\n")

    assert paths.migrate_from_legacy()
    assert paths.config_file().read_text() == '{"audio": "pc"}'
    assert (paths.state_dir() / "density.json").exists(), "pending phone restores move too"
    assert paths.log_file().read_text() == "old log\n"
    assert not old_cfg.exists()
    assert paths.migrate_from_legacy() == [], "second run does nothing"


def test_does_not_overwrite_existing_phonnect_data(tmp_path, monkeypatch):
    _isolated(tmp_path, monkeypatch)
    paths.config_dir(paths.LEGACY_APP).mkdir(parents=True)
    (paths.config_dir(paths.LEGACY_APP) / "config.json").write_text("old")
    paths.config_dir().mkdir(parents=True)
    paths.config_file().write_text("new")
    paths.migrate_from_legacy()
    assert paths.config_file().read_text() == "new"


def test_nothing_to_migrate(tmp_path, monkeypatch):
    _isolated(tmp_path, monkeypatch)
    assert paths.migrate_from_legacy() == []
