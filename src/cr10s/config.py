"""Load and validate ~/.config/cr10s/config.toml (see contracts/config.md)."""

import os
import re
import tomllib
import warnings
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

DEFAULT_PATH = Path("~/.config/cr10s/config.toml")
TOPIC_PLACEHOLDER = "REPLACE_WITH_RANDOM_TOPIC"
TOPIC_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
MB = 1024 * 1024
TRUE_WORDS = {"1", "true", "yes", "on"}
FALSE_WORDS = {"0", "false", "no", "off"}


class ConfigError(Exception):
    """A bad config file or value. The CLI exits with ``exit_code``."""

    exit_code = 1

    def __init__(self, message: str, key: str | None = None):
        super().__init__(f"{key}: {message}" if key else message)
        self.key = key


class ConfigWarning(UserWarning):
    pass


@dataclass(frozen=True)
class PadConfig:
    url: str
    timeout_s: float


@dataclass(frozen=True)
class UploadConfig:
    path: str


@dataclass(frozen=True)
class WatchConfig:
    poll_s: float
    unreachable_after: int
    stall_min: int


@dataclass(frozen=True)
class NotifyConfig:
    desktop: bool
    ntfy_url: str
    ntfy_topic: str = field(repr=False)


@dataclass(frozen=True)
class LogConfig:
    dir: Path
    retention_days: int
    max_bytes: int


@dataclass(frozen=True)
class Config:
    pad: PadConfig
    upload: UploadConfig
    watch: WatchConfig
    notify: NotifyConfig
    log: LogConfig


def _range(low: float, high: float | None = None):
    def check(value):
        if value < low or (high is not None and value > high):
            span = f"between {low:g} and {high:g}" if high is not None else f"at least {low:g}"
            return f"must be {span}"

    return check


def _url(value):
    if not value.startswith(("http://", "https://")):
        return "must start with http:// or https://"


def _upload_path(value):
    if not value or value.startswith("/") or ".." in PurePosixPath(value).parts:
        return "must be a relative path without '..'"


def _topic(value):
    if value and value != TOPIC_PLACEHOLDER and not TOPIC_RE.fullmatch(value):
        return "must be 1-64 characters from A-Z a-z 0-9 _ -"


# section -> key -> (default, type, check). A default of None is computed by default_log_dir().
SCHEMA = {
    "pad": {
        "url": ("http://sonicpad.lan", str, _url),
        "timeout_s": (10.0, float, _range(1, 60)),
    },
    "upload": {"path": ("auto", str, _upload_path)},
    "watch": {
        "poll_s": (5.0, float, _range(2, 60)),
        "unreachable_after": (3, int, _range(1)),
        "stall_min": (15, int, _range(0)),
    },
    "notify": {
        "desktop": (True, bool, None),
        "ntfy_url": ("https://ntfy.sh", str, None),
        "ntfy_topic": ("", str, _topic),
    },
    "log": {
        "dir": (None, str, None),
        "retention_days": (180, int, _range(1)),
        "max_bytes": (50 * MB, int, _range(MB)),
    },
}


def _coerce_env(raw: str, kind: type, key: str):
    try:
        if kind is bool:
            word = raw.strip().lower()
            if word not in TRUE_WORDS | FALSE_WORDS:
                raise ValueError
            return word in TRUE_WORDS
        return kind(raw)
    except ValueError:
        raise ConfigError(f"expected {kind.__name__} in environment override", key) from None


def _check_type(value, kind: type, key: str):
    if kind is float and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    if type(value) is not kind:
        raise ConfigError(f"expected {kind.__name__}", key)
    return value


def default_log_dir() -> Path:
    state = os.environ.get("XDG_STATE_HOME")
    base = Path(state) if state else Path.home() / ".local" / "state"
    return base / "cr10s"


def _read(path: Path | None) -> dict:
    explicit = path is not None
    path = (path if explicit else DEFAULT_PATH).expanduser()
    if not explicit and not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except (OSError, tomllib.TOMLDecodeError) as err:
        raise ConfigError(f"cannot read {path}: {err}") from None


def load(path: str | os.PathLike | None = None) -> Config:
    raw = _read(Path(path) if path is not None else None)

    for section in raw:
        if section not in SCHEMA:
            warnings.warn(f"unknown config section '{section}'", ConfigWarning, stacklevel=2)

    values: dict[str, dict] = {}
    for section, keys in SCHEMA.items():
        table = raw.get(section, {})
        if not isinstance(table, dict):
            raise ConfigError("expected a table", section)
        for name in table.keys() - keys.keys():
            warnings.warn(f"unknown config key '{section}.{name}'", ConfigWarning, stacklevel=2)
        values[section] = {}
        for name, (default, kind, check) in keys.items():
            key = f"{section}.{name}"
            env = os.environ.get(f"CR10S_{section}_{name}".upper())
            if env is not None:
                value = _coerce_env(env, kind, key)
            elif name in table:
                value = _check_type(table[name], kind, key)
            else:
                value = default
            if value is not None and check and (problem := check(value)):
                raise ConfigError(problem, key)
            values[section][name] = value

    topic = values["notify"]["ntfy_topic"]
    if topic == TOPIC_PLACEHOLDER:
        warnings.warn(
            "notify.ntfy_topic is still the placeholder; phone alerts (ntfy) are off",
            ConfigWarning,
            stacklevel=2,
        )
        values["notify"]["ntfy_topic"] = ""

    log_dir = values["log"]["dir"]
    values["log"]["dir"] = Path(log_dir).expanduser() if log_dir else default_log_dir()

    return Config(
        pad=PadConfig(**values["pad"]),
        upload=UploadConfig(**values["upload"]),
        watch=WatchConfig(**values["watch"]),
        notify=NotifyConfig(**values["notify"]),
        log=LogConfig(**values["log"]),
    )
