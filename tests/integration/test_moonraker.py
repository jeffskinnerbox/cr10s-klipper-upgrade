"""Integration tests for cr10s.moonraker against the fake Moonraker (T021)."""

import hashlib
import json
import socket
import time

import pytest

from cr10s import cli, log, moonraker

pytestmark = pytest.mark.integration

GCODE = b"G28\nG1 X10\n"
SHA = hashlib.sha256(GCODE).hexdigest()


@pytest.fixture
def gcode_file(tmp_path):
    path = tmp_path / "part.gcode"
    path.write_bytes(GCODE)
    return path


@pytest.fixture
def client(fake_moonraker):
    with moonraker.Moonraker(fake_moonraker.url, 2) as mr:
        yield mr


def test_server_info(client):
    assert client.server_info()["klippy_state"] == "ready"


def test_query_objects_asks_for_the_contract_set(client, fake_moonraker):
    fake_moonraker.set_states(fake_moonraker.state(print_state="printing"))
    status = client.query_objects()
    assert status["print_stats"]["state"] == "printing"
    (call,) = fake_moonraker.calls("/printer/objects/query")
    assert set(call.args) == set(moonraker.QUERY_OBJECTS)


def test_upload_sends_print_false_and_the_checksum(client, fake_moonraker, gcode_file):
    result = client.upload(gcode_file, "proj", SHA)
    assert result["item"]["path"] == "proj/part.gcode"
    assert result["print_started"] is False
    (up,) = fake_moonraker.uploads
    assert up.fields == {"root": "gcodes", "print": "false", "checksum": SHA, "path": "proj"}
    assert up.content == GCODE


def test_upload_name_override_and_no_dir(client, fake_moonraker, gcode_file):
    client.upload(gcode_file, None, SHA, name="renamed.gcode")
    assert "renamed.gcode" in fake_moonraker.gcodes
    assert "path" not in fake_moonraker.uploads[0].fields


def test_bad_checksum_raises_checksum_mismatch_and_keeps_the_old_file(
    client, fake_moonraker, gcode_file
):
    fake_moonraker.gcodes["proj/part.gcode"] = b"old"
    with pytest.raises(cli.ChecksumMismatch) as exc:
        client.upload(gcode_file, "proj", "0" * 64)
    assert exc.value.status == 422
    assert exc.value.exit_code == 3
    assert fake_moonraker.gcodes["proj/part.gcode"] == b"old"


def test_pad_fork_quirks_500_checksum_mismatch_and_unwrapped_reply(
    client, fake_moonraker, gcode_file
):
    fake_moonraker.pad_style = True
    with pytest.raises(cli.ChecksumMismatch) as exc:
        client.upload(gcode_file, "proj", "0" * 64)
    assert exc.value.status == 500
    assert exc.value.exit_code == 3
    assert "proj/part.gcode" not in fake_moonraker.gcodes
    reply = client.upload(gcode_file, "proj", SHA)
    assert reply["item"]["path"] == "proj/part.gcode"
    assert reply["print_started"] is False


def test_metadata_and_missing_metadata(client, fake_moonraker, gcode_file):
    client.upload(gcode_file, "proj", SHA)
    assert client.metadata("proj/part.gcode")["estimated_time"] == 3600.0
    fake_moonraker.metadata_enabled = False
    assert client.metadata("proj/part.gcode") is None


def test_delete_gcode(client, fake_moonraker, gcode_file):
    client.upload(gcode_file, "proj", SHA)
    client.delete_gcode("proj/part.gcode")
    assert fake_moonraker.gcodes == {}
    with pytest.raises(cli.Rejected) as exc:
        client.delete_gcode("proj/part.gcode")
    assert exc.value.status == 404


def test_config_listing_and_download(client, fake_moonraker):
    names = {f["path"] for f in client.list_config()}
    assert names == set(fake_moonraker.config_files)
    assert client.get_config_file("printer.cfg") == fake_moonraker.config_files["printer.cfg"]


def test_host_error_raises_rejected_with_status(client, fake_moonraker):
    fake_moonraker.set_states(503)
    with pytest.raises(cli.Rejected) as exc:
        client.query_objects()
    assert exc.value.status == 503
    assert "503" in str(exc.value)


def test_closed_port_raises_unreachable():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    with moonraker.Moonraker(f"http://127.0.0.1:{port}", 2) as mr, pytest.raises(cli.Unreachable):
        mr.server_info()


def test_hung_host_raises_unreachable_within_the_timeout(fake_moonraker):
    fake_moonraker.hang()
    start = time.monotonic()
    with moonraker.Moonraker(fake_moonraker.url, 1) as mr, pytest.raises(cli.Unreachable):
        mr.server_info()
    assert time.monotonic() - start < 1 + 1


def test_requests_are_logged(fake_moonraker, tmp_path):
    lg = log.get("status", log_dir=tmp_path)
    with moonraker.Moonraker(fake_moonraker.url, 2, lg) as mr:
        mr.server_info()
        fake_moonraker.set_states(500)
        with pytest.raises(cli.Rejected):
            mr.query_objects()
    recs = [json.loads(x) for x in (tmp_path / "status.jsonl").read_text().splitlines()]
    assert [r["event"] for r in recs] == ["http_request", "http_request", "http_error"]
    assert recs[0]["details"]["path"] == "/server/info"
    assert recs[0]["details"]["status"] == 200
    assert recs[2]["details"]["status"] == 500


def test_there_is_no_way_to_start_a_print():
    public = [n for n in dir(moonraker.Moonraker) if not n.startswith("_")]
    assert not [n for n in public if "start" in n or "print" in n]
