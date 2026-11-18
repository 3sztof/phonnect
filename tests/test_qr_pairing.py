from phonnect.adb import MdnsService
from phonnect.wireless import KnownDevices, QrPairing, new_qr_pairing, pair_and_connect, qr_pairing_address


class FakeAdb:
    def __init__(self, services=(), pair_output="Successfully paired to 192.168.1.20:41234 [guid=adb-ZZ9-AbCdEf]"):
        self.services = list(services)
        self.pair_output = pair_output
        self.paired = []

    def mdns_services(self):
        return self.services

    def pair(self, address, code):
        self.paired.append((address, code))
        return "Successfully paired" in self.pair_output, self.pair_output


def test_qr_code_text_follows_androids_format():
    p = QrPairing("phonnect-Ab12Cd34", "secret123456")
    assert p.text == "WIFI:T:ADB;S:phonnect-Ab12Cd34;P:secret123456;;"


def test_each_pairing_gets_its_own_name_and_password():
    a, b = new_qr_pairing(), new_qr_pairing()
    assert a.name.startswith("phonnect-") and a.name != b.name
    assert len(a.password) >= 10 and a.password.isalnum()


def test_phone_is_found_only_by_its_pairing_service_name():
    p = QrPairing("phonnect-Ab12Cd34", "pw")
    adb = FakeAdb(
        [
            MdnsService("adb-ZZ9-AbCdEf", "_adb-tls-connect._tcp", "192.168.1.20:37099"),
            MdnsService("phonnect-Other000", "_adb-tls-pairing._tcp", "192.168.1.30:41000"),
        ]
    )
    assert qr_pairing_address(adb, p) is None
    adb.services.append(MdnsService("phonnect-Ab12Cd34", "_adb-tls-pairing._tcp.", "192.168.1.20:41234"))
    assert qr_pairing_address(adb, p) == "192.168.1.20:41234"


def test_failed_pairing_is_reported(tmp_path):
    adb = FakeAdb(pair_output="Failed: Wrong password or connection was dropped.")
    known = KnownDevices(tmp_path / "known.json", paired=set)
    ok, message = pair_and_connect(adb, known, "192.168.1.20:41234", "pw")
    assert not ok and "Wrong password" in message
    assert adb.paired == [("192.168.1.20:41234", "pw")]
