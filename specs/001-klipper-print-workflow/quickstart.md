# Quickstart: Validate the Workflow

Run guide that proves the feature works end to end. Commands and contracts are in
[contracts/](contracts/). Phase details are in [plan.md](plan.md#build-phases).

## Prerequisites

- Ubuntu desktop with `uv`, `openscad`, OrcaSlicer AppImage on `PATH` as `orca-slicer`,
  `xvfb`, `libnotify-bin`, `shellcheck`, `pre-commit`.
- The Sonic Pad on the LAN at `sonicpad.lan`, with the desktop in `trusted_clients`.
- `~/.config/cr10s/config.toml` made from `config.example.toml`, with a random `ntfy_topic`.
  Subscribe to that topic in the ntfy phone app.

## 1. Offline checks (no hardware)

```bash
uv sync
make check            # ruff + shellcheck + markdownlint + pytest -m "unit or integration"
pre-commit run -a     # gitleaks etc.
```

Expected: all pass. The integration tests show that the upload never sends `print=true`, that a
bad checksum gives exit 3, that a hung host gives exit 2 within 15 s, that the watcher sends one
alert per change, and that prune removes old records and halves oversized files.

## 2. Live Pad checks (printer idle, bed clear)

```bash
uv run pytest -m live --live
uv run cr10s-status
```

Expected: status shows `klippy_state: ready` and `print_state: standby`. The live upload test
uploads and deletes a file, and the state stays `standby`.

## 3. One command from model to Pad

```bash
cp -r templates/model-project ~/src/models/test-cube && cd ~/src/models/test-cube
make upload && make upload    # second run should skip export/slice
uv run cr10s-status
```

Expected: done in < 3 min. The file shows in Fluidd with time and filament. No print starts.

## 4. Monitoring

```bash
make install                  # installs user units
systemctl --user status cr10s-watch cr10s-log-prune.timer
```

Start the test cube from Fluidd, then pause, resume and cancel it. Expected: a desktop popup and
phone push within 30 s for each event. `jq -c 'select(.tool=="watch")' ~/.local/state/cr10s/watch.jsonl`
shows the state changes.

## 5. Backup

```bash
uv run cr10s-backup
git log -1 --stat
```

Expected: a commit with `printer/config/*` changes only, or `backup_no_change` if there was no diff.

## 6. Hardware acceptance

Follow `docs/build/phase-NN-*.md` and record each exit test in `docs/build/test-log.md`.
Core sign-off (Phase 10) needs US1–US7 and SC-001…SC-010 to pass.
