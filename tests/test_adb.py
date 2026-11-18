from phonnect.adb import EMULATOR, USB, WIRELESS, Device, parse_devices, parse_mdns
from phonnect.tools import parse_scrcpy_version

WINDOWS_OUTPUT = """\
List of devices attached
1A2B3C4D5E6F7G         device product:caiman model:Pixel_9_Pro device:caiman transport_id:3
emulator-5562          offline transport_id:1

"""

LINUX_OUTPUT = """\
* daemon not running; starting now at tcp:5037
* daemon started successfully
List of devices attached
ABC123                 no permissions (missing udev rules? user is in the plugdev group); see [http://developer.android.com/tools/device.html] usb:1-1
DEF456                 unauthorized usb:1-2 transport_id:2
192.168.1.20:5555      device product:x model:Pixel_7 device:x transport_id:4
adb-1A2B3C4D5E6F7G-Ab12Cd._adb-tls-connect._tcp device product:caiman model:Pixel_9_Pro device:caiman transport_id:5
"""


def test_parse_windows_output():
    devices = parse_devices(WINDOWS_OUTPUT)
    assert devices == [
        Device("1A2B3C4D5E6F7G", "device", "Pixel_9_Pro"),
        Device("emulator-5562", "offline", ""),
    ]
    assert devices[0].transport == USB
    assert devices[0].online
    assert devices[0].label == "Pixel 9 Pro (USB)"
    assert devices[1].transport == EMULATOR
    assert devices[1].label == "emulator-5562 (emulator)"
    assert not devices[1].online


def test_parse_linux_output_states_and_transports():
    devices = parse_devices(LINUX_OUTPUT)
    assert [(d.serial, d.state, d.transport) for d in devices] == [
        ("ABC123", "no permissions", USB),
        ("DEF456", "unauthorized", USB),
        ("192.168.1.20:5555", "device", WIRELESS),
        ("adb-1A2B3C4D5E6F7G-Ab12Cd._adb-tls-connect._tcp", "device", WIRELESS),
    ]
    assert devices[3].label == "Pixel 9 Pro (Wi-Fi)"


def test_parse_empty():
    assert parse_devices("List of devices attached\n\n") == []


def test_parse_mdns():
    text = """List of discovered mdns services
adb-1A2B3C4D5E6F7G-Ab12Cd\t_adb-tls-connect._tcp\t192.168.1.20:37099
adb-1A2B3C4D5E6F7G-Ab12Cd\t_adb-tls-pairing._tcp.\t192.168.1.20:41234
"""
    services = parse_mdns(text)
    assert [(s.service, s.address) for s in services] == [
        ("_adb-tls-connect._tcp", "192.168.1.20:37099"),
        ("_adb-tls-pairing._tcp", "192.168.1.20:41234"),
    ]


def test_parse_scrcpy_version():
    assert parse_scrcpy_version("scrcpy 3.3.4 <https://github.com/Genymobile/scrcpy>") == (3, 3)
    assert parse_scrcpy_version("scrcpy v1.25\n") == (1, 25)
    assert parse_scrcpy_version("garbage") is None
