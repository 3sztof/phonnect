import socket

from scrcpy_autolaunch.adb import Device
from scrcpy_autolaunch.wireless import (
    KnownDevices,
    paired_guid,
    paired_serials,
    scan_ports,
    split_address,
    status_of,
)

HW = "1A2B3C4D5E6F7G"


def test_paired_serials_reads_adb_known_hosts(tmp_path):
    # adb_known_hosts.pb is protobuf; the names are plain ASCII inside it.
    path = tmp_path / "adb_known_hosts.pb"
    path.write_bytes(b"\n\x1b\n\x19adb-1A2B3C4D5E6F7G-B9Mtzc\n\x1b\n\x19adb-ZZ9-AbCdEf")
    assert paired_serials(path) == {HW, "ZZ9"}
    assert paired_serials(tmp_path / "missing.pb") == set()


def test_paired_guid():
    out = "Successfully paired to 192.168.1.132:41234 [guid=adb-1A2B3C4D5E6F7G-B9Mtzc]"
    assert paired_guid(out) == HW
    assert paired_guid("Failed: Wrong password or connection was dropped.") is None


def test_split_address():
    assert split_address("192.168.1.132:44191") == ("192.168.1.132", 44191)
    assert split_address("adb-x._adb-tls-connect._tcp") is None


def test_known_devices_merge_paired_and_persist(tmp_path):
    store = KnownDevices(tmp_path / "w.json", paired=lambda: {HW, "OTHER"})
    labels = {d.hw_id for d in store.all()}
    assert labels == {HW, "OTHER"}

    store.remember(HW, model="Pixel_9_Pro", address="192.168.1.132:44191")
    again = KnownDevices(tmp_path / "w.json", paired=lambda: set())
    d = again.get(HW)
    assert d.label == "Pixel 9 Pro"
    assert d.ip == "192.168.1.132" and d.address == "192.168.1.132:44191"


def test_known_devices_reload_written_by_other_process(tmp_path):
    a = KnownDevices(tmp_path / "w.json", paired=set)
    b = KnownDevices(tmp_path / "w.json", paired=set)
    a.remember(HW, ip="10.0.0.5")
    assert b.get(HW) is not None and b.get(HW).ip == "10.0.0.5"


def test_status_of(tmp_path):
    store = KnownDevices(tmp_path / "w.json", paired=set)
    store.remember(HW, address="192.168.1.132:44191")
    k = store.get(HW)
    assert status_of(k, []) == "not connected"
    assert status_of(k, [Device(HW, "device")]) == "USB"
    assert status_of(k, [Device("192.168.1.132:40000", "device")]) == "Wi-Fi"
    assert status_of(k, [Device("192.168.1.132:44191", "offline")]) == "Wi-Fi (offline)"
    assert status_of(k, [Device(f"adb-{HW}-B9Mtzc._adb-tls-connect._tcp", "device")]) == "Wi-Fi"


def test_scan_ports_finds_listener():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    port = server.getsockname()[1]
    try:
        assert scan_ports("127.0.0.1", ports=range(port - 5, port + 5)) == [port]
    finally:
        server.close()
