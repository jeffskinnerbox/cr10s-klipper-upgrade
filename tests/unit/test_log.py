"""Unit tests for cr10s.log (T010).

Interface these tests pin down for T018:

* ``log.get(tool, log_dir=None, verbose=False) -> Logger``. ``log_dir=None`` means
  ``$XDG_STATE_HOME/cr10s``, else ``~/.local/state/cr10s``.
  Records go to ``<log_dir>/<tool>.jsonl``.
* ``Logger.debug/info/warning/error(event, msg, **details)`` append one record.
* ``Logger.run()`` is a context manager that writes ``run_start`` and ``run_end``.
* ``verbose=True`` mirrors ``msg`` to stderr.
"""

import json
import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cr10s import log

pytestmark = pytest.mark.unit

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
REQUIRED = {"ts", "level", "tool", "event", "run_id", "msg"}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("CR10S_RUN_ID", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_one_json_object_per_line(tmp_path):
    lg = log.get("upload", log_dir=tmp_path)
    lg.info("upload_ok", "first")
    lg.error("checksum_mismatch", "second")
    raw = (tmp_path / "upload.jsonl").read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r" not in raw
    lines = raw.decode("utf-8").split("\n")[:-1]
    assert len(lines) == 2
    assert all(isinstance(json.loads(line), dict) for line in lines)


def test_required_fields_and_file_name_match_tool(tmp_path):
    log.get("status", log_dir=tmp_path).info("http_request", "GET /server/info")
    (rec,) = records(tmp_path / "status.jsonl")
    assert REQUIRED <= rec.keys()
    assert rec["tool"] == "status"
    assert rec["event"] == "http_request"
    assert rec["msg"] == "GET /server/info"
    assert rec["level"] == "INFO"


def test_details_is_optional(tmp_path):
    lg = log.get("export", log_dir=tmp_path)
    lg.info("export_ok", "no details")
    lg.info("export_ok", "with details", file="a.stl", size=12)
    plain, rich = records(tmp_path / "export.jsonl")
    assert "details" not in plain
    assert rich["details"] == {"file": "a.stl", "size": 12}


@pytest.mark.parametrize("name", ["debug", "info", "warning", "error"])
def test_level_names(tmp_path, name):
    getattr(log.get("watch", log_dir=tmp_path), name)("state_change", "x")
    (rec,) = records(tmp_path / "watch.jsonl")
    assert rec["level"] == name.upper()


def test_ts_is_utc_millisecond_z(tmp_path):
    before = datetime.now(UTC).replace(microsecond=0)
    log.get("slice", log_dir=tmp_path).info("slice_ok", "x")
    (rec,) = records(tmp_path / "slice.jsonl")
    assert TS_RE.match(rec["ts"])
    ts = datetime.strptime(rec["ts"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
    assert before <= ts <= datetime.now(UTC) + timedelta(seconds=1)


def test_run_id_is_uuid4_and_shared_by_one_logger(tmp_path):
    lg = log.get("upload", log_dir=tmp_path)
    lg.info("upload_ok", "a")
    lg.info("upload_ok", "b")
    first, second = records(tmp_path / "upload.jsonl")
    assert uuid.UUID(first["run_id"]).version == 4
    assert first["run_id"] == second["run_id"]


def test_each_new_process_style_logger_gets_a_new_run_id(tmp_path):
    log.get("upload", log_dir=tmp_path).info("upload_ok", "a")
    log.get("upload", log_dir=tmp_path).info("upload_ok", "b")
    first, second = records(tmp_path / "upload.jsonl")
    assert first["run_id"] != second["run_id"]


def test_run_id_is_inherited_from_env(tmp_path, monkeypatch):
    rid = str(uuid.uuid4())
    monkeypatch.setenv("CR10S_RUN_ID", rid)
    log.get("slice", log_dir=tmp_path).info("slice_ok", "a")
    log.get("upload", log_dir=tmp_path).info("upload_ok", "b")
    assert records(tmp_path / "slice.jsonl")[0]["run_id"] == rid
    assert records(tmp_path / "upload.jsonl")[0]["run_id"] == rid


def test_msg_is_capped_at_200_chars(tmp_path):
    log.get("export", log_dir=tmp_path).info("export_ok", "x" * 500)
    (rec,) = records(tmp_path / "export.jsonl")
    assert len(rec["msg"]) <= 200


def test_non_ascii_round_trips_as_utf8(tmp_path):
    log.get("export", log_dir=tmp_path).info("export_ok", "bracket – Ø 12 mm ✔")
    (rec,) = records(tmp_path / "export.jsonl")
    assert rec["msg"] == "bracket – Ø 12 mm ✔"


@pytest.mark.parametrize(
    "key",
    ["ntfy_topic", "topic", "NTFY_TOPIC", "api_token", "Token", "password", "db_password_old"],
)
def test_secret_looking_keys_are_masked(tmp_path, key):
    log.get("watch", log_dir=tmp_path).info("alert_sent", "x", **{key: "hunter2"})
    (rec,) = records(tmp_path / "watch.jsonl")
    assert rec["details"][key] == "***"
    assert "hunter2" not in (tmp_path / "watch.jsonl").read_text()


def test_nested_secret_keys_are_masked(tmp_path):
    log.get("watch", log_dir=tmp_path).info(
        "alert_sent", "x", notify={"ntfy_topic": "hunter2", "url": "https://ntfy.sh"}
    )
    (rec,) = records(tmp_path / "watch.jsonl")
    assert rec["details"]["notify"] == {"ntfy_topic": "***", "url": "https://ntfy.sh"}


def test_ordinary_keys_are_not_masked(tmp_path):
    log.get("upload", log_dir=tmp_path).info("upload_ok", "x", file="a.gcode", sha256="ab12")
    (rec,) = records(tmp_path / "upload.jsonl")
    assert rec["details"] == {"file": "a.gcode", "sha256": "ab12"}


def test_records_append_across_loggers(tmp_path):
    log.get("upload", log_dir=tmp_path).info("upload_ok", "a")
    log.get("upload", log_dir=tmp_path).info("upload_ok", "b")
    assert [r["msg"] for r in records(tmp_path / "upload.jsonl")] == ["a", "b"]


def test_log_dir_is_created(tmp_path):
    target = tmp_path / "deep" / "er"
    log.get("backup", log_dir=target).info("backup_no_change", "x")
    assert (target / "backup.jsonl").exists()


def test_default_dir_is_home_local_state(tmp_path):
    log.get("prune").info("prune_done", "x")
    assert (tmp_path / "home" / ".local" / "state" / "cr10s" / "prune.jsonl").exists()


def test_default_dir_follows_xdg_state_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg"))
    log.get("prune").info("prune_done", "x")
    assert (tmp_path / "xdg" / "cr10s" / "prune.jsonl").exists()


def test_unwritable_dir_warns_on_stderr_and_keeps_running(tmp_path, capsys):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x")
    lg = log.get("upload", log_dir=blocker / "logs")
    lg.info("upload_ok", "one")
    lg.error("http_error", "two")
    err = capsys.readouterr().err
    assert "log" in err.lower()
    assert err.count("\n") >= 1


def test_unwritable_dir_warns_only_once(tmp_path, capsys):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x")
    lg = log.get("upload", log_dir=blocker / "logs")
    for _ in range(5):
        lg.info("upload_ok", "x")
    assert len(capsys.readouterr().err.strip().splitlines()) == 1


def test_verbose_mirrors_msg_to_stderr(tmp_path, capsys):
    log.get("status", log_dir=tmp_path, verbose=True).info("http_request", "GET /printer/info")
    assert "GET /printer/info" in capsys.readouterr().err


def test_quiet_by_default(tmp_path, capsys):
    log.get("status", log_dir=tmp_path).info("http_request", "GET /printer/info")
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""


def test_run_writes_start_and_end_with_one_run_id(tmp_path):
    lg = log.get("slice", log_dir=tmp_path)
    with lg.run():
        lg.info("slice_ok", "middle")
    start, mid, end = records(tmp_path / "slice.jsonl")
    assert (start["event"], mid["event"], end["event"]) == ("run_start", "slice_ok", "run_end")
    assert start["run_id"] == mid["run_id"] == end["run_id"]
    assert end["level"] == "INFO"


def test_run_logs_error_end_and_reraises(tmp_path):
    lg = log.get("slice", log_dir=tmp_path)
    with pytest.raises(RuntimeError, match="boom"), lg.run():
        raise RuntimeError("boom")
    *_, end = records(tmp_path / "slice.jsonl")
    assert end["event"] == "run_end"
    assert end["level"] == "ERROR"


def test_env_is_not_polluted_by_get(tmp_path):
    log.get("upload", log_dir=tmp_path).info("upload_ok", "x")
    assert "CR10S_RUN_ID" not in os.environ
