"""Shared CLI plumbing: common options, exit codes, and the run() wrapper."""

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace

from cr10s import config, log

OK = 0
USAGE = 1
UNREACHABLE = 2
REJECTED = 3
LOCAL_TOOL = 4
SAFETY = 5
INTERRUPTED = 130


class CliError(Exception):
    """A failure with a fixed exit code. ``event`` is the log event it is recorded under."""

    exit_code = LOCAL_TOOL
    event = "tool_failed"


class UsageError(CliError):
    exit_code = USAGE
    event = "usage_error"


class Unreachable(CliError):
    exit_code = UNREACHABLE
    event = "host_unreachable"


class Rejected(CliError):
    exit_code = REJECTED
    event = "http_error"

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class ChecksumMismatch(Rejected):
    event = "checksum_mismatch"


class LocalToolError(CliError):
    exit_code = LOCAL_TOOL
    event = "tool_failed"


class SafetyRefusal(CliError):
    exit_code = SAFETY
    event = "safety_refusal"


@dataclass(frozen=True)
class Context:
    args: argparse.Namespace
    config: config.Config
    log: log.Logger


def common_parser() -> argparse.ArgumentParser:
    """Parent parser holding the options every command shares."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--config", metavar="PATH", help="config file (default: ~/.config/cr10s/config.toml)"
    )
    parent.add_argument("--pad", metavar="URL", help="Pad base URL, overrides the config")
    parent.add_argument(
        "-v", "--verbose", action="store_true", help="mirror log messages to stderr"
    )
    parent.add_argument("--json", action="store_true", help="machine-readable output on stdout")
    return parent


def _parse(parser: argparse.ArgumentParser, argv: list[str] | None):
    """Return the parsed args, or an exit code when argparse already handled the call."""
    try:
        return parser.parse_args(argv)
    except SystemExit as exit_:
        # argparse exits 2 on bad usage, but 2 means "unreachable" here.
        return OK if exit_.code in (None, 0) else USAGE


def _load(args: argparse.Namespace) -> config.Config:
    cfg = config.load(args.config)
    if args.pad:
        problem = config.SCHEMA["pad"]["url"][2](args.pad)
        if problem:
            raise config.ConfigError(problem, "pad.url")
        cfg = replace(cfg, pad=replace(cfg.pad, url=args.pad))
    return cfg


def run(
    tool: str,
    parser: argparse.ArgumentParser,
    body: Callable[[Context], int | None],
    argv: list[str] | None = None,
) -> int:
    """Parse, load config, run ``body`` inside a logged run, and return the exit code."""
    args = _parse(parser, argv)
    if isinstance(args, int):
        return args
    try:
        cfg = _load(args)
    except config.ConfigError as err:
        print(f"{parser.prog}: {err}", file=sys.stderr)
        return err.exit_code

    logger = log.get(tool, log_dir=cfg.log.dir, verbose=args.verbose)

    def guarded() -> int | None:
        # Log the failure before logger.run() writes run_end.
        try:
            return body(Context(args, cfg, logger))
        except CliError as err:
            logger.error(err.event, str(err))
            raise
        except Exception as err:
            logger.error("unhandled_exception", f"{type(err).__name__}: {err}")
            raise

    try:
        with logger.run():
            return guarded() or OK
    except CliError as err:
        print(f"{parser.prog}: {err}", file=sys.stderr)
        return err.exit_code
    except KeyboardInterrupt:
        return INTERRUPTED
    except Exception as err:
        print(f"{parser.prog}: unexpected error: {err}", file=sys.stderr)
        return LOCAL_TOOL
