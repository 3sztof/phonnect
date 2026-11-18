from scrcpy_autolaunch.adb import Device
from scrcpy_autolaunch.tray import build_rows
from scrcpy_autolaunch.wireless import KnownDevice

HW = "1A2B3C4D5E6F7G"
USB = Device(HW, "device", "Pixel_9_Pro")
WIFI = Device("192.168.1.132:37457", "device", "Pixel_9_Pro")


def test_phone_on_usb_and_wifi_is_one_row():
    rows = build_rows([(HW, [USB, WIFI], True)], [KnownDevice(HW, "Pixel_9_Pro")], set())
    assert len(rows) == 1
    r = rows[0]
    assert (r.name, r.state, r.via_text, r.wifi_serial) == ("Pixel 9 Pro", "mirroring", "USB + Wi-Fi", WIFI.serial)


def test_known_but_disconnected_phone_is_offered_and_sorted_last():
    other = KnownDevice("ZZ1", "Pixel_7")
    rows = build_rows([(HW, [USB], False)], [KnownDevice(HW), other], {"nothing"})
    assert [(r.name, r.state) for r in rows] == [("Pixel 9 Pro", "connected"), ("Pixel 7", "available")]


def test_connecting_and_unauthorized_states():
    unauth = Device("XYZ", "unauthorized")
    rows = build_rows([("XYZ", [unauth], False)], [KnownDevice("ZZ1", "Pixel_7")], {"ZZ1"})
    assert {r.name: r.state for r in rows} == {"XYZ": "unauthorized", "Pixel 7": "connecting"}


def test_unnamed_connected_phone_takes_known_name():
    nameless = Device(HW, "device", "")
    rows = build_rows([(HW, [nameless], False)], [KnownDevice(HW, "Pixel_9_Pro")], set())
    assert rows[0].name == "Pixel 9 Pro"
