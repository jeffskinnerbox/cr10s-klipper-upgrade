# Data Model

Phase 1 output for [plan.md](plan.md). Entities come from the [spec](spec.md#key-entities).

## Config

Loaded from `~/.config/cr10s/config.toml`. Env vars `CR10S_<SECTION>_<KEY>` override it.
The file is never in the repo. Schema: [contracts/config.md](contracts/config.md).

| Field                    | Type   | Default                       | Rule                              |
| :----------------------- | :----- | :---------------------------- | :-------------------------------- |
| `pad.url`                | str    | `http://sonicpad.lan`         | must start with `http://` or `https://` |
| `pad.timeout_s`          | float  | 10                            | 1–60                              |
| `upload.path`            | str    | `auto`                        | relative, no `..`                 |
| `watch.poll_s`           | float  | 5                             | 2–60                              |
| `watch.unreachable_after`| int    | 3                             | consecutive failed polls          |
| `watch.stall_min`        | int    | 15                            | 0 disables the check              |
| `notify.desktop`         | bool   | true                          |                                   |
| `notify.ntfy_url`        | str    | `https://ntfy.sh`             |                                   |
| `notify.ntfy_topic`      | str    | empty (phone alerts off)      | secret; 1–64 chars `[A-Za-z0-9_-]` |
| `log.dir`                | path   | `$XDG_STATE_HOME/cr10s`       |                                   |
| `log.retention_days`     | int    | 180                           | ≥1                                |
| `log.max_bytes`          | int    | 52428800 (50 MB)              | ≥1 MB                             |

## LogRecord

One JSON object per line. Schema: [contracts/log-record.md](contracts/log-record.md).

| Field     | Type     | Rule                                          |
| :-------- | :------- | :-------------------------------------------- |
| `ts`      | str      | UTC ISO-8601 with `Z`, used for age pruning   |
| `level`   | str      | `DEBUG`/`INFO`/`WARNING`/`ERROR`              |
| `tool`    | str      | `upload`, `status`, `watch`, `slice`, `prune`, `backup`, `make` |
| `event`   | str      | snake_case, stable (e.g. `upload_ok`, `checksum_mismatch`) |
| `run_id`  | str      | UUID; inherited from `CR10S_RUN_ID` if set    |
| `msg`     | str      | short human text                              |
| `details` | object   | any extra fields; never secrets               |

## PrintFile

| Field            | Source                       |
| :--------------- | :--------------------------- |
| `local_path`     | build output                 |
| `remote_path`    | `<upload.path>/<name>.gcode` |
| `sha256`         | computed before upload       |
| `size`           | bytes                        |
| `estimated_time` | Moonraker metadata (s), optional |
| `filament_total` | Moonraker metadata (mm), optional |

## PrinterState (one poll snapshot)

| Field            | From Moonraker                     |
| :--------------- | :--------------------------------- |
| `reachable`      | HTTP success                       |
| `klippy_state`   | `webhooks.state` (`ready`, `startup`, `shutdown`, `error`, `disconnected`) |
| `print_state`    | `print_stats.state` (`standby`, `printing`, `paused`, `complete`, `cancelled`, `error`) |
| `filename`       | `print_stats.filename`             |
| `progress`       | `virtual_sdcard.progress` (0–1)    |
| `extruder_temp`, `bed_temp` | `extruder.temperature`, `heater_bed.temperature` |
| `message`        | `print_stats.message` / `webhooks.state_message` |

## Watcher state machine

The watcher compares each snapshot with the previous one and sends an **Alert** on each change:

```text
host:    REACHABLE --(N failed polls)--> UNREACHABLE --(poll ok)--> REACHABLE
           alert: host_unreachable (once)          alert: host_recovered

klippy:  ready --> shutdown|error|disconnected     alert: klipper_down
         (not ready) --> ready                     alert: klipper_ready

print:   standby|complete|cancelled --> printing   alert: print_started
         printing --> paused                       alert: print_paused (incl. filament message if present)
         paused --> printing                       alert: print_resumed
         printing|paused --> complete              alert: print_complete
         printing|paused --> cancelled             alert: print_cancelled
         * --> error                               alert: print_error
         printing, progress unchanged ≥ stall_min  alert: print_stalled (once per stall)
```

The first snapshot after start (or after the desktop wakes) sends one `watch_started` summary,
not one alert per change.

## Alert

| Field      | Rule                                           |
| :--------- | :--------------------------------------------- |
| `kind`     | one of the alerts above                        |
| `title`    | e.g. `CR-10S: print complete`                  |
| `body`     | file, progress, temps, message                 |
| `priority` | `high` for error/klipper_down/unreachable/paused, otherwise `default` |
| `targets`  | `desktop`, `ntfy`. Each one is sent and logged separately |

## ConfigBackup

| Field          | Rule                                                    |
| :------------- | :------------------------------------------------------ |
| `files`        | all files under the Moonraker `config` root, except `*.bkp` and logs |
| `dest`         | `printer/config/`                                       |
| `commit`       | only if there is a diff. The message lists the files that changed |
| `secret_check` | gitleaks must pass before commit                        |

## BuildPhase (docs)

| Field     | Rule                                                |
| :-------- | :-------------------------------------------------- |
| `id`      | 00–16                                               |
| `guide`   | `docs/build/phase-NN-<name>.md`                     |
| `wiring`  | links to `docs/wiring/*.md` used in this phase      |
| `test`    | numbered pass/fail checks                           |
| `result`  | row in `docs/build/test-log.md`: date, pass/fail, notes |
