"""Unit tests for cr10s.cli (T020).

``cli.run(tool, parser, body, argv=None) -> int`` parses ``argv``, loads the config (``--pad``
beats the file and env), opens the logger, runs ``body(ctx)`` inside ``logger.run()`` and maps
errors to the exit codes in contracts/cli.md. ``ctx`` has ``args``, ``config`` and ``log``.
"""

import argparse
import json
import os

import pytest

from cr10s import cli

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.startswith("CR10S_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)


@pytest.fixture
def cfg(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(f'[log]\ndir = "{tmp_path / "logs"}"\n')
    return path


def parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(prog="cr10s-demo", parents=[cli.common_parser()])


def records(tmp_path):
    return [json.loads(x) for x in (tmp_path / "logs" / "demo.jsonl").read_text().splitlines()]


def call(cfg, body, *extra):
    return cli.run("demo", parser(), body, ["--config", str(cfg), *extra])


def test_exit_codes_match_the_contract():
    assert (cli.OK, cli.USAGE, cli.UNREACHABLE) == (0, 1, 2)
    assert (cli.REJECTED, cli.LOCAL_TOOL, cli.SAFETY) == (3, 4, 5)


def test_common_options_and_defaults():
    args = parser().parse_args([])
    assert (args.config, args.pad, args.verbose, args.json) == (None, None, False, False)
    args = parser().parse_args(["--config", "c.toml", "--pad", "http://x", "-v", "--json"])
    assert (args.config, args.pad, args.verbose, args.json) == ("c.toml", "http://x", True, True)


def test_returns_the_body_exit_code(cfg):
    assert call(cfg, lambda ctx: 3) == 3


def test_none_means_ok(cfg):
    assert call(cfg, lambda ctx: None) == 0


def test_body_gets_args_config_and_logger(cfg, tmp_path):
    seen = {}

    def body(ctx):
        seen["json"] = ctx.args.json
        seen["dir"] = ctx.config.log.dir
        ctx.log.info("export_ok", "hello")

    assert call(cfg, body, "--json") == 0
    assert seen == {"json": True, "dir": tmp_path / "logs"}
    events = [r["event"] for r in records(tmp_path)]
    assert events == ["run_start", "export_ok", "run_end"]


def test_pad_flag_overrides_config(cfg):
    urls = []
    call(cfg, lambda ctx: urls.append(ctx.config.pad.url), "--pad", "http://other.lan:7125")
    assert urls == ["http://other.lan:7125"]


def test_bad_pad_flag_exits_1(cfg, capsys):
    assert call(cfg, lambda ctx: 0, "--pad", "ftp://nope") == 1
    assert "pad.url" in capsys.readouterr().err


def test_bad_config_exits_1_with_the_key(tmp_path, capsys):
    bad = tmp_path / "bad.toml"
    bad.write_text("[pad]\ntimeout_s = 0\n")
    assert cli.run("demo", parser(), lambda ctx: 0, ["--config", str(bad)]) == 1
    assert "pad.timeout_s" in capsys.readouterr().err


def test_usage_error_exits_1_not_2(capsys):
    assert cli.run("demo", parser(), lambda ctx: 0, ["--nope"]) == 1
    assert "--nope" in capsys.readouterr().err


def test_help_exits_0(capsys):
    assert cli.run("demo", parser(), lambda ctx: 1, ["--help"]) == 0
    assert "--config" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("error", "code", "event"),
    [
        (cli.Unreachable("no route"), 2, "host_unreachable"),
        (cli.Rejected("HTTP 422"), 3, "http_error"),
        (cli.LocalToolError("openscad failed"), 4, "tool_failed"),
        (cli.SafetyRefusal("would start a print"), 5, "safety_refusal"),
        (cli.UsageError("empty file"), 1, "usage_error"),
    ],
)
def test_errors_map_to_exit_code_message_and_log(cfg, tmp_path, capsys, error, code, event):
    def body(ctx):
        raise error

    assert call(cfg, body) == code
    assert str(error) in capsys.readouterr().err
    recs = records(tmp_path)
    assert [r["event"] for r in recs] == ["run_start", event, "run_end"]
    assert recs[1]["level"] == "ERROR"
    assert recs[-1]["level"] == "ERROR"


def test_unexpected_exception_is_a_local_failure(cfg, tmp_path, capsys):
    def body(ctx):
        raise RuntimeError("bug")

    assert call(cfg, body) == 4
    assert "bug" in capsys.readouterr().err
    events = [r["event"] for r in records(tmp_path)]
    assert "unhandled_exception" in events


def test_ctrl_c_exits_130(cfg, tmp_path):
    def body(ctx):
        raise KeyboardInterrupt

    assert call(cfg, body) == 130
    assert records(tmp_path)[-1]["event"] == "run_end"


def test_verbose_mirrors_log_to_stderr(cfg, capsys):
    call(cfg, lambda ctx: ctx.log.info("export_ok", "visible"), "-v")
    assert "visible" in capsys.readouterr().err
