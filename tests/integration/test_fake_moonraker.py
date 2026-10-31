"""Self-test of the fake Moonraker (T012): it must behave as the contract says."""

import hashlib
import time

import httpx
import pytest

pytestmark = pytest.mark.integration

GCODE = b"G28\nG1 X10\n"
SHA = hashlib.sha256(GCODE).hexdigest()


def upload(fake, *, checksum=SHA, print_flag="false", path="proj"):
    return httpx.post(
        f"{fake.url}/server/files/upload",
        data={"root": "gcodes", "path": path, "print": print_flag, "checksum": checksum},
        files={"file": ("part.gcode", GCODE)},
    )


def test_server_info(fake_moonraker):
    body = httpx.get(f"{fake_moonraker.url}/server/info").json()
    assert body["result"]["klippy_state"] == "ready"


def test_query_plays_back_the_script_and_repeats_the_last(fake_moonraker):
    s = fake_moonraker.state
    fake_moonraker.set_states(s(), s(print_state="printing", progress=0.5, filename="a.gcode"))
    url = f"{fake_moonraker.url}/printer/objects/query?webhooks&print_stats&virtual_sdcard"
    states = [httpx.get(url).json()["result"]["status"]["print_stats"]["state"] for _ in range(3)]
    assert states == ["standby", "printing", "printing"]


def test_query_returns_only_requested_objects(fake_moonraker):
    status = httpx.get(f"{fake_moonraker.url}/printer/objects/query?webhooks").json()
    assert set(status["result"]["status"]) == {"webhooks"}


def test_scripted_http_error(fake_moonraker):
    fake_moonraker.set_states(fake_moonraker.state(), 503)
    url = f"{fake_moonraker.url}/printer/objects/query?webhooks"
    assert httpx.get(url).status_code == 200
    assert httpx.get(url).status_code == 503


def test_good_upload_is_201_and_never_starts_a_print(fake_moonraker):
    resp = upload(fake_moonraker)
    assert resp.status_code == 201
    result = resp.json()["result"]
    assert result["item"]["path"] == "proj/part.gcode"
    assert result["print_started"] is False
    assert fake_moonraker.gcodes["proj/part.gcode"] == GCODE
    assert fake_moonraker.uploads[0].fields["print"] == "false"


def test_bad_checksum_is_422_and_stores_nothing(fake_moonraker):
    resp = upload(fake_moonraker, checksum="0" * 64)
    assert resp.status_code == 422
    assert fake_moonraker.gcodes == {}
    assert fake_moonraker.uploads[0].accepted is False


def test_bad_checksum_does_not_replace_an_existing_file(fake_moonraker):
    fake_moonraker.gcodes["proj/part.gcode"] = b"old"
    upload(fake_moonraker, checksum="0" * 64)
    assert fake_moonraker.gcodes["proj/part.gcode"] == b"old"


def test_checksum_ignored_mode_models_a_fork_that_skips_the_check(fake_moonraker):
    fake_moonraker.checksum_mode = "ignore"
    assert upload(fake_moonraker, checksum="0" * 64).status_code == 201


def test_metadata(fake_moonraker):
    upload(fake_moonraker)
    url = f"{fake_moonraker.url}/server/files/metadata?filename=proj/part.gcode"
    result = httpx.get(url).json()["result"]
    assert result["estimated_time"] == 3600.0
    assert result["filament_total"] == 1500.0


def test_metadata_can_be_unavailable(fake_moonraker):
    upload(fake_moonraker)
    fake_moonraker.metadata_enabled = False
    url = f"{fake_moonraker.url}/server/files/metadata?filename=proj/part.gcode"
    assert httpx.get(url).status_code == 404


def test_delete(fake_moonraker):
    upload(fake_moonraker)
    resp = httpx.delete(f"{fake_moonraker.url}/server/files/gcodes/proj/part.gcode")
    assert resp.status_code == 200
    assert fake_moonraker.gcodes == {}
    assert (
        httpx.delete(f"{fake_moonraker.url}/server/files/gcodes/proj/part.gcode").status_code == 404
    )


def test_config_list_and_download(fake_moonraker):
    listing = httpx.get(f"{fake_moonraker.url}/server/files/list?root=config").json()["result"]
    assert {f["path"] for f in listing} == set(fake_moonraker.config_files)
    body = httpx.get(f"{fake_moonraker.url}/server/files/config/printer.cfg")
    assert body.content == fake_moonraker.config_files["printer.cfg"]


def test_hang_mode_trips_the_client_timeout(fake_moonraker):
    fake_moonraker.hang()
    start = time.monotonic()
    with pytest.raises(httpx.TimeoutException):
        httpx.get(f"{fake_moonraker.url}/server/info", timeout=0.5)
    assert time.monotonic() - start < 3


def test_hang_can_be_released(fake_moonraker):
    fake_moonraker.hang()
    fake_moonraker.hang(False)
    assert httpx.get(f"{fake_moonraker.url}/server/info", timeout=5).status_code == 200


def test_print_start_is_a_contract_violation(fake_moonraker):
    resp = httpx.post(f"{fake_moonraker.url}/printer/print/start", params={"filename": "x"})
    assert resp.status_code == 403
    assert fake_moonraker.contract_violations()
    fake_moonraker.forbidden.clear()  # keep teardown green: this test provoked it on purpose


def test_print_true_is_a_contract_violation(fake_moonraker):
    upload(fake_moonraker, print_flag="true")
    assert any("print=false" in p for p in fake_moonraker.contract_violations())
    fake_moonraker.uploads.clear()


def test_unknown_endpoint_is_a_contract_violation(fake_moonraker):
    assert httpx.get(f"{fake_moonraker.url}/machine/reboot").status_code == 404
    assert fake_moonraker.contract_violations()
    fake_moonraker.unexpected.clear()
