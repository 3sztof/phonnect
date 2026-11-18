import subprocess

from phonnect.adb import Adb
from phonnect.wireless import KnownDevice, reconnect


class HangingAdb(Adb):
    """An adb whose every command times out, like a phone that stopped answering."""

    def __init__(self):
        super().__init__("adb")

    def run(self, *args, timeout=15):
        raise subprocess.TimeoutExpired(["adb", *args], timeout)


def test_connect_timeout_is_a_failure_not_a_crash():
    ok, message = HangingAdb().connect("192.168.1.20:37099")
    assert not ok and "timed out after 20 s" in message


def test_pair_timeout_is_a_failure_not_a_crash():
    ok, message = HangingAdb().pair("192.168.1.20:41234", "123456")
    assert not ok and "timed out" in message


def test_reconnect_reports_a_hanging_adb():
    device = KnownDevice("ZZ9", model="Pixel_7", address="192.168.1.20:37099", ip="192.168.1.20")
    ok, message = reconnect(HangingAdb(), device, scan=False)
    assert not ok and "didn't answer" in message


def test_failed_connect_output_is_not_success():
    class FakeAdb(Adb):
        def run(self, *args, timeout=15):
            return subprocess.CompletedProcess(args, 0, "failed to connect to 192.168.1.20:37099", "")

    ok, _ = FakeAdb("adb").connect("192.168.1.20:37099")
    assert not ok
