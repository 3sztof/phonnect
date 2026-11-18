import json

from phonnect import __version__, updates
from phonnect.osutil import IS_WINDOWS


def test_versions_compare_numerically():
    assert updates.is_newer("0.10.0", "0.9.3")
    assert updates.is_newer("3.4", (3, 3))
    assert updates.is_newer("1.0.1", "1.0")
    assert not updates.is_newer("1.0", "1.0.0")
    assert not updates.is_newer("0.3.0", "0.3.0")
    assert not updates.is_newer(None, "1.0")
    assert not updates.is_newer("v-weird", "1.0")


def test_check_asks_github_at_most_once_a_day():
    calls = []

    def fetch(repo):
        calls.append(repo)
        return {"3sztof/phonnect": "9.9.9", "Genymobile/scrcpy": "4.0"}[repo]

    first = updates.check(fetch=fetch, now=lambda: 1_000_000)
    assert (first.phonnect, first.scrcpy) == ("9.9.9", "4.0")
    assert len(calls) == 2
    again = updates.check(fetch=fetch, now=lambda: 1_000_000 + 3600)
    assert again.phonnect == "9.9.9" and len(calls) == 2  # served from the cache
    updates.check(fetch=fetch, now=lambda: 1_000_000 + 25 * 3600)
    assert len(calls) == 4
    assert json.loads(updates.cache_file().read_text())["phonnect"] == "9.9.9"


def test_a_failed_check_keeps_what_was_known_and_retries_soon():
    updates.check(fetch=lambda repo: "9.9.9", now=lambda: 1_000)
    failed = updates.check(force=True, fetch=lambda repo: None, now=lambda: 2_000)
    assert failed.phonnect == "9.9.9"
    assert failed.checked_at == 1_000  # not counted as a successful check


def test_update_is_offered_only_for_newer_releases():
    assert updates.phonnect_update(updates.Releases(phonnect="999.0.0")) == "999.0.0"
    assert updates.phonnect_update(updates.Releases(phonnect=__version__)) is None
    assert updates.scrcpy_update(updates.Releases(scrcpy="3.4"), (3, 3)) == "3.4"
    assert updates.scrcpy_update(updates.Releases(scrcpy="3.3"), (3, 3)) is None
    assert updates.scrcpy_update(updates.Releases(scrcpy="3.4"), None) is None


def test_update_check_rejects_tags_that_arent_plain_versions():
    # A tag ends up in the updater's command line: anything but digits and dots is refused.
    assert updates.strict_version("v1.2.3") == "1.2.3"
    assert updates.strict_version("0.10") == "0.10"
    for bad in ("v9.9.9'; Remove-Item x; '", "1.2.3-rc1", "1.2.3;", "$(evil)", "1", "", None, 5):
        assert updates.strict_version(bad) is None, bad


def test_updater_refuses_a_bad_version():
    import pytest

    with pytest.raises(ValueError):
        updates.updater_command("9.9.9'; calc; '")


def test_a_tampered_cache_is_ignored():
    updates.cache_file().parent.mkdir(parents=True, exist_ok=True)
    updates.cache_file().write_text(json.dumps({"phonnect": "9.9.9'; calc; '", "scrcpy": "4.0", "checked_at": 1}))
    cached = updates.load_cache()
    assert cached.phonnect is None and cached.scrcpy == "4.0"
    assert updates.phonnect_update(cached) is None


def test_updater_runs_that_releases_installer_in_update_mode():
    cmd = " ".join(updates.updater_command("1.2.3"))
    if IS_WINDOWS:
        assert "releases/download/v1.2.3/install.ps1" in cmd and "PHONNECT_UPDATE = '1'" in cmd
        assert "PHONNECT_YES" not in cmd
    else:
        assert "releases/download/v1.2.3/install.sh" in cmd and "--update --version 1.2.3" in cmd
        assert "--yes" not in cmd


def test_one_click_update_doesnt_ask_again():
    cmd = " ".join(updates.updater_command("1.2.3", confirm=False))
    assert ("PHONNECT_YES = '1'" in cmd) if IS_WINDOWS else ("--yes" in cmd)


def test_scrcpy_hint_matches_how_it_was_installed():
    winget = r"C:\Users\x\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_x\scrcpy.exe"
    assert "winget upgrade Genymobile.scrcpy" in updates.scrcpy_update_hint(winget)
    assert "scoop update scrcpy" in updates.scrcpy_update_hint(r"C:\Users\x\scoop\shims\scrcpy.exe")
