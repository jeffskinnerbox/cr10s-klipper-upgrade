"""Unit tests for cr10s.prune (T011).

Interface these tests pin down for T019:

* ``prune.prune(log_dir, retention_days, max_bytes, *, dry_run=False, now=None) -> Summary``.
  ``Summary.files`` maps file name to a result with ``before_bytes``, ``after_bytes``,
  ``before_records``, ``after_records`` and ``unparseable``. ``now`` is a tz-aware datetime
  (default: the current time). It prunes every ``*.jsonl`` in ``log_dir``, ignores other files,
  and logs one ``prune_done`` record to ``<log_dir>/prune.jsonl``.
* ``prune.main(argv) -> int`` is the ``cr10s-log-prune`` entry point: ``--config``, ``--dry-run``.
  It returns the exit code and prints a per-file summary on stdout.

Fixture contract for T015 (``tests/fixtures/logs/``, built by ``tests/fixtures/make_logs.py``).
Ages are measured from NOW below, so the committed files carry fixed timestamps:

* ``aged.jsonl``: four valid records, 10, 179, 181 and 400 days old, oldest first.
* ``garbage.jsonl``, one record per line, in this order: a valid record 400 days old; the text
  ``this is not json``; a valid record 10 days old; ``{"no_ts": 1}``; a truncated
  ``{"ts": "2026-``.
"""

import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cr10s import prune

pytestmark = pytest.mark.unit

NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "logs"
BIG = 10**9


def ts(age_days: float) -> str:
    return (NOW - timedelta(days=age_days)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def rec(age_days: float, n: int = 0) -> str:
    return json.dumps(
        {
            "ts": ts(age_days),
            "level": "INFO",
            "tool": "upload",
            "event": "upload_ok",
            "run_id": "00000000-0000-4000-8000-000000000000",
            "msg": f"record {n}",
        }
    )


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")


def msgs(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line)["msg"])
        except (ValueError, KeyError, TypeError):
            out.append(line)
    return out


def ages(path: Path) -> list[int]:
    return [
        round((NOW - datetime.fromisoformat(json.loads(line)["ts"])).total_seconds() / 86400)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


@pytest.fixture
def logs(tmp_path) -> Path:
    d = tmp_path / "logs"
    d.mkdir()
    return d


def run(logs: Path, *, retention_days=180, max_bytes=BIG, dry_run=False):
    return prune.prune(
        logs, retention_days=retention_days, max_bytes=max_bytes, dry_run=dry_run, now=NOW
    )


def test_age_rule_removes_only_records_older_than_retention(logs):
    shutil.copy(FIXTURES / "aged.jsonl", logs / "aged.jsonl")
    run(logs)
    assert ages(logs / "aged.jsonl") == [179, 10]


def test_record_exactly_at_retention_is_kept(logs):
    write_lines(logs / "edge.jsonl", [rec(181, 0), rec(180, 1), rec(179.9, 2)])
    run(logs)
    assert msgs(logs / "edge.jsonl") == ["record 1", "record 2"]


def test_retention_days_is_honoured(logs):
    shutil.copy(FIXTURES / "aged.jsonl", logs / "aged.jsonl")
    run(logs, retention_days=30)
    assert ages(logs / "aged.jsonl") == [10]


def test_summary_counts_and_sizes(logs):
    shutil.copy(FIXTURES / "aged.jsonl", logs / "aged.jsonl")
    before = (logs / "aged.jsonl").stat().st_size
    result = run(logs).files["aged.jsonl"]
    assert result.before_records == 4
    assert result.after_records == 2
    assert result.before_bytes == before
    assert result.after_bytes == (logs / "aged.jsonl").stat().st_size < before
    assert result.unparseable == 0


def test_oversized_file_loses_its_oldest_half(logs):
    write_lines(logs / "big.jsonl", [rec(100 - i * 0.1, i) for i in range(200)])
    size = (logs / "big.jsonl").stat().st_size
    run(logs, max_bytes=size - 1)
    kept = msgs(logs / "big.jsonl")
    assert kept == [f"record {i}" for i in range(100, 200)]


def test_odd_record_count_removes_the_smaller_half(logs):
    write_lines(logs / "odd.jsonl", [rec(5 - i * 0.1, i) for i in range(5)])
    size = (logs / "odd.jsonl").stat().st_size
    run(logs, max_bytes=size - 1)
    assert msgs(logs / "odd.jsonl") == ["record 2", "record 3", "record 4"]


def test_halving_happens_once_even_if_still_over_the_limit(logs):
    write_lines(logs / "big.jsonl", [rec(100 - i * 0.1, i) for i in range(200)])
    run(logs, max_bytes=10)
    assert len(msgs(logs / "big.jsonl")) == 100


def test_file_under_the_limit_is_not_halved(logs):
    write_lines(logs / "ok.jsonl", [rec(5 - i * 0.1, i) for i in range(20)])
    size = (logs / "ok.jsonl").stat().st_size
    run(logs, max_bytes=size)
    assert len(msgs(logs / "ok.jsonl")) == 20


def test_age_rule_runs_before_halving(logs):
    # 4 old + 16 new. Age first leaves 16 records at ~80% of the size, under the 90% limit.
    # Halving first would drop the 10 oldest records and leave only 10.
    old = [rec(400 - i, i) for i in range(4)]
    new = [rec(10 - i * 0.5, 4 + i) for i in range(16)]
    write_lines(logs / "mix.jsonl", old + new)
    total = (logs / "mix.jsonl").stat().st_size
    run(logs, max_bytes=total * 9 // 10)
    assert msgs(logs / "mix.jsonl") == [f"record {i}" for i in range(4, 20)]


def test_unparseable_lines_are_kept_in_place_and_counted(logs):
    shutil.copy(FIXTURES / "garbage.jsonl", logs / "garbage.jsonl")
    result = run(logs).files["garbage.jsonl"]
    assert msgs(logs / "garbage.jsonl") == [
        "this is not json",
        "record 1",
        '{"no_ts": 1}',
        '{"ts": "2026-',
    ]
    assert result.unparseable == 3
    assert result.before_records == 5
    assert result.after_records == 4


def test_dry_run_changes_nothing(logs):
    shutil.copy(FIXTURES / "aged.jsonl", logs / "aged.jsonl")
    shutil.copy(FIXTURES / "garbage.jsonl", logs / "garbage.jsonl")
    snapshot = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in logs.iterdir()}
    result = run(logs, dry_run=True)
    assert {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in logs.iterdir()} == snapshot
    assert result.files["aged.jsonl"].after_records == 2


def test_rewrite_goes_through_os_replace_in_the_same_dir(logs, monkeypatch):
    shutil.copy(FIXTURES / "aged.jsonl", logs / "aged.jsonl")
    calls = []
    real = os.replace

    def spy(src, dst):
        calls.append((Path(src), Path(dst)))
        return real(src, dst)

    monkeypatch.setattr(prune.os, "replace", spy)
    run(logs)
    (src, dst), *_ = calls
    assert dst == logs / "aged.jsonl"
    assert src.parent == dst.parent
    assert src != dst


def test_interrupted_rewrite_leaves_original_and_no_temp_files(logs, monkeypatch):
    shutil.copy(FIXTURES / "aged.jsonl", logs / "aged.jsonl")
    original = (logs / "aged.jsonl").read_bytes()

    def boom(src, dst):
        raise OSError("simulated interrupt")

    monkeypatch.setattr(prune.os, "replace", boom)
    with pytest.raises(OSError, match="simulated"):
        run(logs)
    assert (logs / "aged.jsonl").read_bytes() == original
    assert sorted(p.name for p in logs.iterdir() if p.name != "prune.jsonl") == ["aged.jsonl"]


def test_non_jsonl_files_are_ignored(logs):
    (logs / "notes.txt").write_text("keep me\n")
    write_lines(logs / "old.jsonl.bak", [rec(400)])
    run(logs)
    assert (logs / "notes.txt").read_text() == "keep me\n"
    assert msgs(logs / "old.jsonl.bak") == ["record 0"]


def test_logs_prune_done_with_per_file_numbers(logs):
    shutil.copy(FIXTURES / "aged.jsonl", logs / "aged.jsonl")
    before = (logs / "aged.jsonl").stat().st_size
    run(logs)
    done = [
        json.loads(line)
        for line in (logs / "prune.jsonl").read_text().splitlines()
        if json.loads(line)["event"] == "prune_done"
    ]
    assert len(done) == 1
    assert done[0]["tool"] == "prune"
    entry = done[0]["details"]["files"]["aged.jsonl"]
    assert entry["before_records"] == 4
    assert entry["after_records"] == 2
    assert entry["before_bytes"] == before
    assert entry["after_bytes"] == (logs / "aged.jsonl").stat().st_size
    assert entry["unparseable"] == 0


def test_dry_run_does_not_touch_other_files_but_still_reports(logs):
    shutil.copy(FIXTURES / "aged.jsonl", logs / "aged.jsonl")
    run(logs, dry_run=True)
    assert len(msgs(logs / "aged.jsonl")) == 4


def test_empty_and_missing_dirs_are_fine(logs, tmp_path):
    assert run(logs).files == {}
    assert run(tmp_path / "does-not-exist").files == {}


def test_main_uses_config_and_dry_run_flag(logs, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    shutil.copy(FIXTURES / "aged.jsonl", logs / "aged.jsonl")
    before = (logs / "aged.jsonl").read_bytes()
    cfg = tmp_path / "config.toml"
    cfg.write_text(f'[log]\ndir = "{logs}"\nretention_days = 180\nmax_bytes = 1048576\n')
    assert prune.main(["--config", str(cfg), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "aged.jsonl" in out
    assert (logs / "aged.jsonl").read_bytes() == before


def test_main_bad_config_exits_1(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("[log]\nretention_days = 0\n")
    assert prune.main(["--config", str(cfg)]) == 1
