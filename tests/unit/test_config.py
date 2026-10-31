"""Unit tests for cr10s.config (T009).

Interface these tests pin down for T016:

* ``config.load(path=None) -> Config``: frozen dataclass with sections ``pad``, ``upload``,
  ``watch``, ``notify`` and ``log``. ``path=None`` means ``~/.config/cr10s/config.toml``;
  a missing default file gives the defaults.
* ``CR10S_<SECTION>_<KEY>`` env vars override the file.
* Unknown keys and the placeholder ntfy topic emit ``config.ConfigWarning`` (a ``UserWarning``).
* A bad value raises ``config.ConfigError`` with ``.key`` (dotted name) and ``.exit_code == 1``.
"""

import dataclasses
import os
from pathlib import Path

import pytest

from cr10s import config

pytestmark = pytest.mark.unit

MB = 1024 * 1024


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.startswith("CR10S_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)


def write_cfg(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text)
    return path


def bad_value(tmp_path: Path, section: str, key: str, toml_value: str):
    path = write_cfg(tmp_path, f"[{section}]\n{key} = {toml_value}\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load(path)
    return exc.value


def test_defaults_match_data_model():
    cfg = config.load()
    assert cfg.pad.url == "http://sonicpad.lan"
    assert cfg.pad.timeout_s == 10
    assert cfg.upload.path == "auto"
    assert cfg.watch.poll_s == 5
    assert cfg.watch.unreachable_after == 3
    assert cfg.watch.stall_min == 15
    assert cfg.notify.desktop is True
    assert cfg.notify.ntfy_url == "https://ntfy.sh"
    assert cfg.notify.ntfy_topic == ""
    assert cfg.log.retention_days == 180
    assert cfg.log.max_bytes == 52428800


def test_log_dir_defaults_to_home_state(tmp_path):
    assert config.load().log.dir == tmp_path / "home" / ".local" / "state" / "cr10s"


def test_log_dir_follows_xdg_state_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg"))
    assert config.load().log.dir == tmp_path / "xdg" / "cr10s"


def test_default_path_is_read_from_home(tmp_path):
    cfg_dir = tmp_path / "home" / ".config" / "cr10s"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text('[pad]\nurl = "http://pad.example:7125"\n')
    assert config.load().pad.url == "http://pad.example:7125"


def test_file_values_override_defaults(tmp_path):
    path = write_cfg(
        tmp_path,
        '[pad]\nurl = "https://pad.lan"\ntimeout_s = 20\n[watch]\npoll_s = 10\nstall_min = 0\n',
    )
    cfg = config.load(path)
    assert cfg.pad.url == "https://pad.lan"
    assert cfg.pad.timeout_s == 20
    assert cfg.watch.poll_s == 10
    assert cfg.watch.stall_min == 0
    assert cfg.upload.path == "auto"


def test_config_is_frozen():
    cfg = config.load()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.pad = None


def test_env_override_wins_over_file(tmp_path, monkeypatch):
    path = write_cfg(tmp_path, '[pad]\nurl = "http://from-file.lan"\n')
    monkeypatch.setenv("CR10S_PAD_URL", "http://from-env.lan")
    assert config.load(path).pad.url == "http://from-env.lan"


def test_env_override_is_typed(monkeypatch):
    monkeypatch.setenv("CR10S_PAD_TIMEOUT_S", "30")
    monkeypatch.setenv("CR10S_NOTIFY_DESKTOP", "false")
    monkeypatch.setenv("CR10S_NOTIFY_NTFY_TOPIC", "my-topic_1")
    cfg = config.load()
    assert cfg.pad.timeout_s == 30
    assert cfg.notify.desktop is False
    assert cfg.notify.ntfy_topic == "my-topic_1"


def test_bad_env_value_names_the_key(monkeypatch):
    monkeypatch.setenv("CR10S_PAD_TIMEOUT_S", "500")
    with pytest.raises(config.ConfigError) as exc:
        config.load()
    assert exc.value.key == "pad.timeout_s"


def test_unknown_key_warns(tmp_path):
    path = write_cfg(tmp_path, '[pad]\nurl = "http://pad.lan"\ncolour = "red"\n')
    with pytest.warns(config.ConfigWarning, match=r"pad\.colour"):
        cfg = config.load(path)
    assert cfg.pad.url == "http://pad.lan"


def test_unknown_section_warns(tmp_path):
    path = write_cfg(tmp_path, "[extras]\nx = 1\n")
    with pytest.warns(config.ConfigWarning, match="extras"):
        config.load(path)


def test_placeholder_topic_turns_ntfy_off_with_warning(tmp_path):
    path = write_cfg(tmp_path, '[notify]\nntfy_topic = "REPLACE_WITH_RANDOM_TOPIC"\n')
    with pytest.warns(config.ConfigWarning, match="ntfy"):
        cfg = config.load(path)
    assert cfg.notify.ntfy_topic == ""


def test_warning_never_contains_a_real_topic(tmp_path):
    path = write_cfg(tmp_path, '[notify]\nntfy_topic = "s3cret-topic"\nbogus = 1\n')
    with pytest.warns(config.ConfigWarning) as record:
        config.load(path)
    assert all("s3cret-topic" not in str(w.message) for w in record)


def test_error_exit_code_is_1(tmp_path):
    err = bad_value(tmp_path, "pad", "timeout_s", "0")
    assert err.exit_code == 1


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("pad", "url", '"sonicpad.lan"'),
        ("pad", "url", '"ftp://sonicpad.lan"'),
        ("pad", "timeout_s", "0.5"),
        ("pad", "timeout_s", "61"),
        ("pad", "timeout_s", '"ten"'),
        ("upload", "path", '"/abs/path"'),
        ("upload", "path", '"../escape"'),
        ("upload", "path", '"a/../../b"'),
        ("watch", "poll_s", "1"),
        ("watch", "poll_s", "61"),
        ("watch", "unreachable_after", "0"),
        ("watch", "stall_min", "-1"),
        ("notify", "ntfy_topic", '"has space"'),
        ("notify", "ntfy_topic", '"bad/topic"'),
        ("notify", "ntfy_topic", '"' + "a" * 65 + '"'),
        ("log", "retention_days", "0"),
        ("log", "max_bytes", str(MB - 1)),
    ],
)
def test_invalid_value_names_the_key(tmp_path, section, key, value):
    err = bad_value(tmp_path, section, key, value)
    assert err.key == f"{section}.{key}"
    assert f"{section}.{key}" in str(err)


@pytest.mark.parametrize(
    ("section", "key", "value", "attr"),
    [
        ("pad", "url", '"http://a"', "http://a"),
        ("pad", "url", '"https://a:7125"', "https://a:7125"),
        ("pad", "timeout_s", "1", 1),
        ("pad", "timeout_s", "60", 60),
        ("upload", "path", '"projects/widget"', "projects/widget"),
        ("watch", "poll_s", "2", 2),
        ("watch", "poll_s", "60", 60),
        ("watch", "stall_min", "0", 0),
        ("notify", "ntfy_topic", '"a"', "a"),
        ("notify", "ntfy_topic", '"' + "A_-9" * 16 + '"', "A_-9" * 16),
        ("log", "retention_days", "1", 1),
        ("log", "max_bytes", str(MB), MB),
    ],
)
def test_boundary_values_are_accepted(tmp_path, section, key, value, attr):
    path = write_cfg(tmp_path, f"[{section}]\n{key} = {value}\n")
    assert getattr(getattr(config.load(path), section), key) == attr


def test_malformed_toml_exits_1(tmp_path):
    path = write_cfg(tmp_path, "[pad\nurl = ")
    with pytest.raises(config.ConfigError) as exc:
        config.load(path)
    assert exc.value.exit_code == 1


def test_explicit_missing_file_exits_1(tmp_path):
    with pytest.raises(config.ConfigError) as exc:
        config.load(tmp_path / "nope.toml")
    assert exc.value.exit_code == 1
