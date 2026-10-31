# CLI Contract

All commands share these rules:

- `--config PATH`, `--pad URL`, `-v/--verbose` and `--json` (machine-readable stdout).
- Human output goes to stdout and errors to stderr. Every run writes log records
  ([log-record.md](log-record.md)).
- Exit codes: `0` ok · `1` usage/config error · `2` host unreachable/timeout · `3` rejected by
  host (4xx/5xx, checksum) · `4` local tool failure (slicer/openscad) · `5` safety refusal.

## `cr10s-upload FILE.gcode [--path DIR] [--name NAME]`

- Computes the SHA-256 and POSTs to `/server/files/upload` with `root=gcodes`, `print=false`
  and `checksum`.
- **MUST NOT** send `print=true`. There is no flag that enables it. A test asserts the form field.
- Never leaves a partial file: a failed or aborted upload leaves nothing new on the host, and a
  file with the same name is only replaced after the host accepts the checksum.
- Refuses non-`.gcode` files (exit 1). Refuses to upload if the file is empty (exit 1).
- On 201: prints the remote path, plus estimated time and filament if metadata is available.
- On 422: exit 3, event `checksum_mismatch`.
- On connect error or timeout: exit 2 within `timeout_s` + 5 s (≤ 15 s at the default
  `timeout_s` of 10). Once the host has accepted the connection, the upload body has no total
  time cap, so large files on a slow link still finish.

## `cr10s-status [--watch-once]`

- Prints `klippy_state`, `print_state`, file, progress %, extruder/bed temps.
- `--json` emits a PrinterState ([../data-model.md](../data-model.md#printerstate-one-poll-snapshot)).
- Exit 2 if unreachable.

## `cr10s-watch [--once] [--no-desktop] [--no-ntfy]`

- Long-running poll loop. Runs as the `cr10s-watch.service` user unit.
- Sends Alerts per the state machine in [../data-model.md](../data-model.md#watcher-state-machine).
- One target failing never blocks the other (logged as `notify_failed`).
- SIGTERM: logs `watch_stopped` and exits 0.

## `cr10s-export MODEL.scad -o OUT.stl [-D name=value ...]`

- Runs `openscad -q --export-format binstl -o OUT.stl [-D ...] MODEL.scad` with a timeout
  (default 300 s).
- Logs `export_ok` (file, size, seconds) or `export_failed` (exit code, stderr tail). Exit 4 on
  failure or timeout.

## `cr10s-slice MODEL.stl --profiles DIR [--filament NAME] -o OUT.gcode`

- Checks that the `orca-slicer` version matches the one recorded in `printer/profiles/VERSION`.
  On mismatch it warns. With `--strict` it exits 4.
- Runs the OrcaSlicer CLI (through `xvfb-run` when `$DISPLAY` is unset), pulls the plate G-code
  out of the `.gcode.3mf`, and writes `OUT.gcode`.
- Exit 4 with stderr tail logged if the slicer fails or no G-code is found.

## `cr10s-log-prune [--dry-run]`

- For each `*.jsonl` in `log.dir`, removes records with `ts` older than `retention_days`. If a
  file is still over `max_bytes`, it removes the oldest half of its records.
- Lines it can't parse are kept, never dropped silently, and counted in the summary.
- Rewrites files safely (temp file, then `os.replace`).
- Logs `prune_done` with per-file before/after sizes and record counts.

## `cr10s-backup [--no-commit] [--logs]`

- Downloads every file in the Moonraker `config` root to `printer/config/`.
- Runs gitleaks on staged changes. If that fails: exit 5, no commit.
- Commits only if there is a diff. `--logs` also copies `klippy.log` into
  `~/.local/state/cr10s/pad/` (never into git).

## Model-project Makefile (`templates/model-project/Makefile`)

| Target   | Does                                                      |
| :------- | :-------------------------------------------------------- |
| `stl`    | `cr10s-export $(NAME).scad -o build/$(NAME).stl`          |
| `gcode`  | `cr10s-slice build/$(NAME).stl --profiles $(PROFILES) -o build/$(NAME).gcode` |
| `upload` | `cr10s-upload build/$(NAME).gcode --path $(NAME)`         |
| `clean`  | `rm -rf build/`                                           |

Each recipe exports the same `CR10S_RUN_ID`, so all its log records share one run id.
