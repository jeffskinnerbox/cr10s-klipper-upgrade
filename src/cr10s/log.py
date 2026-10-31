"""JSON-lines logging (see contracts/log-record.md). One file per tool in the log dir."""

import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from cr10s.config import default_log_dir

MSG_MAX = 200
SECRET_WORDS = ("topic", "token", "password")


def _mask(value):
    if isinstance(value, dict):
        return {
            k: "***" if any(w in str(k).lower() for w in SECRET_WORDS) else _mask(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_mask(v) for v in value]
    return value


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class Logger:
    def __init__(self, tool: str, log_dir: Path, verbose: bool = False):
        self.tool = tool
        self.path = log_dir / f"{tool}.jsonl"
        self.verbose = verbose
        self.run_id = os.environ.get("CR10S_RUN_ID") or str(uuid.uuid4())
        self._warned = False

    def log(self, level: str, event: str, msg: str, **details) -> None:
        if len(msg) > MSG_MAX:
            msg = msg[: MSG_MAX - 1] + "…"
        record = {
            "ts": _now(),
            "level": level,
            "tool": self.tool,
            "event": event,
            "run_id": self.run_id,
            "msg": msg,
        }
        if details:
            record["details"] = _mask(details)
        self._write(json.dumps(record, ensure_ascii=False, default=str))
        if self.verbose:
            print(f"{level.lower()}: {msg}", file=sys.stderr)

    def debug(self, event: str, msg: str, **details) -> None:
        self.log("DEBUG", event, msg, **details)

    def info(self, event: str, msg: str, **details) -> None:
        self.log("INFO", event, msg, **details)

    def warning(self, event: str, msg: str, **details) -> None:
        self.log("WARNING", event, msg, **details)

    def error(self, event: str, msg: str, **details) -> None:
        self.log("ERROR", event, msg, **details)

    @contextmanager
    def run(self):
        start = time.monotonic()
        self.info("run_start", f"{self.tool} started")
        try:
            yield self
        except BaseException as err:
            seconds = round(time.monotonic() - start, 3)
            self.error("run_end", f"{self.tool} failed", seconds=seconds, error=type(err).__name__)
            raise
        self.info("run_end", f"{self.tool} finished", seconds=round(time.monotonic() - start, 3))

    def _write(self, line: str) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as err:
            if not self._warned:
                self._warned = True
                print(f"cr10s: cannot write log {self.path}: {err}", file=sys.stderr)


def get(tool: str, log_dir: str | os.PathLike | None = None, verbose: bool = False) -> Logger:
    return Logger(tool, Path(log_dir) if log_dir is not None else default_log_dir(), verbose)
