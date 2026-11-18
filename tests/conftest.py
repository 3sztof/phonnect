import pytest


@pytest.fixture(autouse=True)
def isolated_app_folder(tmp_path, monkeypatch):
    """Tests never read or write the real settings, log or remembered phones."""
    monkeypatch.setenv("PHONNECT_HOME", str(tmp_path / "phonnect-home"))
