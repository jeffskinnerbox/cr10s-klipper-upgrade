"""Integration tests for cr10s-status against the fake Moonraker (T013).

Interface these tests pin down for T022: ``status.main(argv) -> int`` is the ``cr10s-status``
entry point. It takes ``--pad URL``, ``--config PATH`` and ``--json``, prints to stdout, and
returns the exit code from contracts/cli.md (0 ok, 2 unreachable or timeout, 3 host error).
"""

import json
import os
import socket
import time

import pytest

from cr10s import status

pytestmark = pytest.mark.integration

PRINTER_STATE_FIELDS = {
    "reachable",
    "klippy_state",
    "print_state",
    "filename",
    "progress",
    "extruder_temp",
    "bed_temp",
    "message",
}
QUERY_OBJECTS = {"webhooks", "print_stats", "virtual_sdcard", "extruder", "heater_bed"}


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.startswith("CR10S_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)


@pytest.fixture
def printing(fake_moonraker):
    fake_moonraker.set_states(
        fake_moonraker.state(
            print_state="printing",
            filename="proj/bracket.gcode",
            progress=0.5,
            extruder=205.3,
            bed=60.1,
        )
    )
    return fake_moonraker


def timeout_config(tmp_path, seconds: int):
    cfg = tmp_path / "config.toml"
    cfg.write_text(f"[pad]\ntimeout_s = {seconds}\n")
    return cfg


def closed_port_url() -> str:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def log_events(tmp_path) -> list[dict]:
    path = tmp_path / "home" / ".local" / "state" / "cr10s" / "status.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_prints_the_state_in_human_form(printing, capsys):
    assert status.main(["--pad", printing.url]) == 0
    out = capsys.readouterr().out
    for expected in ("ready", "printing", "proj/bracket.gcode", "50%", "205.3", "60.1"):
        assert expected in out


def test_json_matches_printer_state(printing, capsys):
    assert status.main(["--pad", printing.url, "--json"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert set(state) == PRINTER_STATE_FIELDS
    assert state["reachable"] is True
    assert state["klippy_state"] == "ready"
    assert state["print_state"] == "printing"
    assert state["filename"] == "proj/bracket.gcode"
    assert state["progress"] == 0.5
    assert state["extruder_temp"] == 205.3
    assert state["bed_temp"] == 60.1


def test_idle_printer(fake_moonraker, capsys):
    assert status.main(["--pad", fake_moonraker.url, "--json"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["print_state"] == "standby"
    assert state["progress"] == 0


def test_klippy_error_message_is_shown(fake_moonraker, capsys):
    fake_moonraker.set_states(
        fake_moonraker.state(klippy="error", message="MCU 'mcu' shutdown: Timer too close")
    )
    assert status.main(["--pad", fake_moonraker.url]) == 0
    out = capsys.readouterr().out
    assert "error" in out
    assert "MCU 'mcu' shutdown: Timer too close" in out


def test_asks_for_exactly_the_contract_objects_once(printing):
    status.main(["--pad", printing.url])
    (call,) = printing.calls("/printer/objects/query")
    assert set(call.args) == QUERY_OBJECTS


def test_pad_flag_beats_config(printing, tmp_path, capsys):
    cfg = tmp_path / "config.toml"
    cfg.write_text('[pad]\nurl = "http://does-not-exist.invalid"\n')
    assert status.main(["--config", str(cfg), "--pad", printing.url]) == 0


def test_env_pad_url_is_used(printing, monkeypatch):
    monkeypatch.setenv("CR10S_PAD_URL", printing.url)
    assert status.main([]) == 0


def test_unreachable_host_exits_2(capsys):
    start = time.monotonic()
    assert status.main(["--pad", closed_port_url()]) == 2
    assert time.monotonic() - start < 5
    assert capsys.readouterr().err.strip()


def test_unreachable_host_with_json_still_reports_state(capsys):
    assert status.main(["--pad", closed_port_url(), "--json"]) == 2
    state = json.loads(capsys.readouterr().out)
    assert set(state) == PRINTER_STATE_FIELDS
    assert state["reachable"] is False


def test_hung_host_exits_2_within_timeout_plus_one_second(fake_moonraker, tmp_path):
    fake_moonraker.hang()
    cfg = timeout_config(tmp_path, 1)
    start = time.monotonic()
    assert status.main(["--config", str(cfg), "--pad", fake_moonraker.url]) == 2
    assert time.monotonic() - start < 1 + 1


def test_host_error_exits_3(fake_moonraker, capsys):
    fake_moonraker.set_states(503)
    assert status.main(["--pad", fake_moonraker.url]) == 3
    assert "503" in capsys.readouterr().err


def test_bad_config_exits_1(tmp_path, fake_moonraker):
    cfg = timeout_config(tmp_path, 0)
    assert status.main(["--config", str(cfg), "--pad", fake_moonraker.url]) == 1


def test_run_is_logged(printing, tmp_path):
    status.main(["--pad", printing.url])
    events = [r["event"] for r in log_events(tmp_path)]
    assert events[0] == "run_start"
    assert "http_request" in events
    assert events[-1] == "run_end"
    assert len({r["run_id"] for r in log_events(tmp_path)}) == 1


def test_unreachable_run_logs_host_unreachable(tmp_path):
    status.main(["--pad", closed_port_url()])
    records = log_events(tmp_path)
    assert "host_unreachable" in [r["event"] for r in records]
    assert records[-1]["event"] == "run_end"
