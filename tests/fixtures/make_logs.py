"""Build the committed fixture logs in tests/fixtures/logs/ (T015).

Timestamps are fixed, measured from NOW, so the files never go stale. Tests that use them pass
the same NOW to the pruner. The contract is in tests/unit/test_prune.py.

    python tests/fixtures/make_logs.py
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
OUT = Path(__file__).resolve().parent / "logs"
RUN_ID = "00000000-0000-4000-8000-000000000000"


def record(age_days: float, n: int) -> str:
    ts = (NOW - timedelta(days=age_days)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return json.dumps(
        {
            "ts": ts,
            "level": "INFO",
            "tool": "upload",
            "event": "upload_ok",
            "run_id": RUN_ID,
            "msg": f"record {n}",
        }
    )


def write(name: str, lines: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text("".join(line + "\n" for line in lines), encoding="utf-8")


def main() -> None:
    # Four valid records, oldest first. 181 and 400 days old are past the 180-day default.
    write("aged.jsonl", [record(age, n) for n, age in enumerate((400, 181, 179, 10))])
    # Mixed valid and invalid lines. Only the 400-day-old record should be pruned.
    write(
        "garbage.jsonl",
        [
            record(400, 0),
            "this is not json",
            record(10, 1),
            '{"no_ts": 1}',
            '{"ts": "2026-',
        ],
    )


if __name__ == "__main__":
    main()
