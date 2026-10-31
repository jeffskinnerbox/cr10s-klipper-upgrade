"""cr10s-log-prune: trim the JSON-lines logs by age, then by size (see contracts/cli.md)."""

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cr10s import config, log


@dataclass
class FileResult:
    before_bytes: int
    after_bytes: int
    before_records: int
    after_records: int
    unparseable: int


@dataclass
class Summary:
    dry_run: bool
    files: dict[str, FileResult] = field(default_factory=dict)


def _timestamp(line: bytes) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(json.loads(line)["ts"])
    except (ValueError, KeyError, TypeError):
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)


def _size(lines: list[bytes]) -> int:
    return sum(len(line) + 1 for line in lines)


def _rewrite(path: Path, lines: list[bytes]) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.writelines(line + b"\n" for line in lines)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _prune_file(path: Path, cutoff: datetime, max_bytes: int, dry_run: bool) -> FileResult:
    raw = path.read_bytes()
    lines = raw.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    stamps = [_timestamp(line) for line in lines]
    unparseable = stamps.count(None)

    # Age rule: unparseable lines are never dropped.
    kept = [(line, s) for line, s in zip(lines, stamps, strict=True) if s is None or s >= cutoff]

    # Size rule: still too big, so drop the oldest half of the parseable records.
    if _size([line for line, _ in kept]) > max_bytes:
        drop = sum(1 for _, s in kept if s is not None) // 2
        trimmed = []
        for line, s in kept:
            if s is not None and drop > 0:
                drop -= 1
                continue
            trimmed.append((line, s))
        kept = trimmed

    new_lines = [line for line, _ in kept]
    changed = len(new_lines) != len(lines)
    if changed and not dry_run:
        _rewrite(path, new_lines)
    return FileResult(
        before_bytes=len(raw),
        after_bytes=_size(new_lines) if changed else len(raw),
        before_records=len(lines),
        after_records=len(new_lines),
        unparseable=unparseable,
    )


def prune(
    log_dir: str | os.PathLike,
    retention_days: int,
    max_bytes: int,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
) -> Summary:
    log_dir = Path(log_dir)
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    summary = Summary(dry_run=dry_run)
    if not log_dir.is_dir():
        return summary
    for path in sorted(log_dir.glob("*.jsonl")):
        summary.files[path.name] = _prune_file(path, cutoff, max_bytes, dry_run)
    if not dry_run:
        files = {name: asdict(result) for name, result in summary.files.items()}
        log.get("prune", log_dir=log_dir).info(
            "prune_done", f"pruned {len(files)} log file(s)", files=files
        )
    return summary


def _print(summary: Summary) -> None:
    if summary.dry_run:
        print("dry run: nothing was changed")
    for name, r in summary.files.items():
        note = f", {r.unparseable} unparseable kept" if r.unparseable else ""
        print(
            f"{name}: {r.before_records} -> {r.after_records} records, "
            f"{r.before_bytes} -> {r.after_bytes} bytes{note}"
        )
    if not summary.files:
        print("no log files found")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cr10s-log-prune", description=__doc__)
    parser.add_argument("--config", help="path to config.toml")
    parser.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    try:
        cfg = config.load(args.config)
    except config.ConfigError as err:
        print(f"cr10s-log-prune: {err}", file=sys.stderr)
        return err.exit_code

    def run() -> Summary:
        return prune(cfg.log.dir, cfg.log.retention_days, cfg.log.max_bytes, dry_run=args.dry_run)

    if args.dry_run:
        summary = run()
    else:
        with log.get("prune", log_dir=cfg.log.dir, verbose=args.verbose).run():
            summary = run()
    _print(summary)
    return 0
