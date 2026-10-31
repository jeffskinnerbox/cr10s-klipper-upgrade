# Config Contract

Path: `~/.config/cr10s/config.toml` (or `--config`). It is outside the repo and never committed.
The repo ships `config.example.toml` with placeholders only.

```toml
[pad]
url = "http://sonicpad.lan"      # add :7125 or :7128 if Moonraker is not behind the UI port
timeout_s = 10

[upload]
path = "auto"

[watch]
poll_s = 5
unreachable_after = 3
stall_min = 15

[notify]
desktop = true
ntfy_url = "https://ntfy.sh"
ntfy_topic = "REPLACE_WITH_RANDOM_TOPIC"   # secret; empty disables phone alerts

[log]
# dir defaults to $XDG_STATE_HOME/cr10s (~/.local/state/cr10s)
retention_days = 180
max_bytes = 52428800
```

Rules:

- Unknown keys trigger a warning. Bad values trigger exit 1 with the key name.
- Env overrides: `CR10S_PAD_URL`, `CR10S_NOTIFY_NTFY_TOPIC` and so on.
- `ntfy_topic` is never logged. Log records show `"ntfy_topic": "***"`.
- If `ntfy_topic` is still the placeholder, phone alerts are turned off and a warning is logged.
