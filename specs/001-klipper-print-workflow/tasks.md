---

description: "Task list for CR-10S Klipper Upgrade and Automated Print Workflow"
---

<!-- markdownlint-disable MD013 -- one task per line for /speckit-implement -->

# Tasks: CR-10S Klipper Upgrade and Automated Print Workflow

**Input**: Design documents from `specs/001-klipper-print-workflow/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: REQUIRED. Spec FR-024 to FR-026 and Constitution IV ask for unit tests, integration tests
against a fake Moonraker, opt-in live tests, and a pass/fail exit test for each phase.
Write each test first and confirm it fails before writing the code it checks.

**Organization**: the `## Phase N` headings below are spec-kit stages, not build phases.
Tasks say "Plan Phase N" when they mean a build phase in plan.md, which also numbers the
`docs/build/phase-NN-*.md` guides. Tasks are grouped by user story. The "Plan phase" note on each story maps it to
the build phases in [plan.md](plan.md#build-phases).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks).
- **[Story]**: the user story the task belongs to (US1 to US8).
- **Operator:** the owner does the physical step by hand. Claude writes the guide and the owner
  records the result in `docs/build/test-log.md`. Tasks without this prefix are written by Claude.
- Each hardware story ends with a **gate** task. The next hardware story starts only after the gate
  is recorded as PASS (Constitution I).

## Path Conventions

Single project at repo root: `src/cr10s/`, `tests/`, `printer/`, `docs/build/`, `docs/wiring/`,
`systemd/` and `templates/`, per [plan.md](plan.md#project-structure).

## Constitution Check

| Principle | Enforced by |
| :-- | :-- |
| I. Phased and testable | Gate task at the end of each hardware story; the next story waits for PASS |
| II. Safety first | Pre-power checklist in every wiring task; heater drills in T042; `print=false` tests T064, T068 and the T012 guard |
| III. Portable config | Standard sections only (T033, T040); backup T090; restore drill T091 |
| IV. Test-backed | Tests written first in every story; `make check` in T023 |
| V. Observable | Logger T018; export T071, slice T072, upload T070, status T022, watch T082, prune T019 and backup T090 all log; prune timer T084 |
| VI. No secrets | gitleaks T004 and T007; backup scan T090; history scan T107 |

Each gate task records `II ✔` and `VI ✔` in the `Constitution` column of `docs/build/test-log.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: repo tooling, lint and secret scanning, before any code (Plan Phase 0, first half).

- [X] T001 Create directory skeleton with `.gitkeep` files: `src/cr10s/`, `tests/unit/`, `tests/integration/`, `tests/live/`, `tests/fixtures/`, `printer/config/`, `printer/firmware/`, `printer/profiles/`, `docs/build/`, `docs/wiring/`, `systemd/`, `templates/model-project/`
- [X] T002 Create `pyproject.toml` (uv, `requires-python = ">=3.12"`, package `cr10s` in `src/` layout). Runtime dependency: `httpx`. Dev group: `pytest`, `pytest-httpserver`, `ruff`, `pre-commit`. Console scripts `cr10s-export`, `cr10s-upload`, `cr10s-status`, `cr10s-watch`, `cr10s-slice`, `cr10s-log-prune`, `cr10s-backup` pointing at `cr10s.<module>:main`. Run `uv sync` to make `uv.lock`
- [X] T003 [P] Configure ruff (line-length 100, rules `E,F,W,I,B,UP,S`) and pytest markers `unit`, `integration`, `live` in `pyproject.toml`. Add a `--live` option in `tests/conftest.py` that skips `live`-marked tests unless it is given
- [X] T004 [P] Create `.pre-commit-config.yaml` with gitleaks, ruff (check + format), shellcheck (`shellcheck-py`), and markdownlint-cli2 set to `fix: false` via `.markdownlint-cli2.ci.jsonc`. Copy the rules from the dotfiles config but add `"fix": false`, and exclude `.claude/` and `.specify/` (vendored)
- [X] T005 [P] Add to `.gitignore`: `build/`, `*.jsonl`, `.venv/`, `printer/firmware/*.bin`, `.pytest_cache/`, `.ruff_cache/` (`.env*` and `config.toml` are already there)
- [X] T006 Create the root `Makefile` (`.RECIPEPREFIX = >`) with targets `lint` (ruff, shellcheck `bin/*` and `templates/**/*.sh`, markdownlint with the CI config), `test` (`uv run pytest -m "unit or integration"`), `test-live` (`uv run pytest -m live --live`), `check` (lint + test), `sync-docs` (`bin/sync-docs`) and `install` (left as a stub until T085)
- [X] T007 Run `pre-commit install`. Check that a staged file holding a fake `ghp_` + 36 alphanumerics is blocked by gitleaks. Record the result in `docs/build/test-log.md`, creating it with columns `Date | Phase/Task | Test | Result | Constitution | Notes`
- [X] T008 Create `docs/build/_template.md`, the required layout for every `docs/build/phase-NN-*.md` guide: Purpose, Parts and tools, Risky steps and recovery (each irreversible or risky step, such as firmware flash, mains or heater wiring, and how to undo or recover it), Steps (numbered, each with a photo checkpoint `📷 <what the photo must show>`), Pre-power checklist (if anything is wired), Exit test (numbered pass/fail checks), and Record (the row to add to `docs/build/test-log.md`)

**Checkpoint**: `make lint` passes on an empty package. A committed secret is blocked.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: config, logging, log pruning, the Moonraker client, the fake Moonraker, status, and the
Pad on the network (Plan Phases 0 and 1). Every story depends on these.

**⚠️ CRITICAL**: no user story work starts until this phase is complete.

### Tests (write first, must fail)

- [X] T009 [P] Unit tests for config loading in `tests/unit/test_config.py`: defaults match data-model (`pad.url` default `http://sonicpad.lan`, "must start with `http://` or `https://`"; `pad.timeout_s` "1–60"; `watch.poll_s` "2–60"; `upload.path` "relative, no `..`"; `notify.ntfy_topic` "1–64 chars `[A-Za-z0-9_-]`"; `log.retention_days` "≥1"; `log.max_bytes` "≥1 MB"). Also: env override `CR10S_PAD_URL` wins; unknown key warns; an invalid value exits with code 1 and the key name; a placeholder `REPLACE_WITH_RANDOM_TOPIC` turns ntfy off with a warning
- [X] T010 [P] Unit tests for the logger in `tests/unit/test_log.py`: one JSON object per line with required fields `ts` (UTC, millisecond precision, `Z`), `level`, `tool`, `event`, `run_id` (UUID4, inherited from `CR10S_RUN_ID`), `msg` (≤ 200 chars); `details` keys named like `*topic*`, `*token*` or `*password*` are masked as `***`; an unwritable log dir warns on stderr and the tool keeps running
- [X] T011 [P] Unit tests for pruning in `tests/unit/test_prune.py` using fixtures from T015: records older than 180 days are removed and newer ones kept; a file still over `max_bytes` after the age rule loses its oldest half; lines it can't parse are kept and counted; `--dry-run` changes nothing; the rewrite is atomic (no partial file if interrupted, simulated by mocking `os.replace`)
- [X] T012 [P] Build the fake Moonraker fixture in `tests/integration/conftest.py` on `pytest-httpserver`. It serves every endpoint in [contracts/moonraker-subset.md](contracts/moonraker-subset.md), with scripted state snapshots, 422 on a bad checksum, a recorded upload form, a "hang" mode, and a guard that fails the test if `/printer/print/start` is called
- [X] T013 [P] Integration tests for the client and status in `tests/integration/test_status.py`: `cr10s-status` prints `klippy_state`, `print_state`, file, progress and temps; `--json` matches the PrinterState fields in data-model; host unreachable gives exit 2; hang mode gives exit 2 within `timeout_s` + 1 s
- [X] T014 [P] Live test in `tests/live/test_pad_info.py`: `GET /server/info` returns `klippy_state`, and the print state is `standby` before and after

### Implementation

- [X] T015 [P] Create fixture logs in `tests/fixtures/logs/` with `tests/fixtures/make_logs.py`: `aged.jsonl` (records 10, 179, 181 and 400 days old), `oversized.jsonl` (made on the fly at about 60 MB during the test, not committed), and `garbage.jsonl` (mixed valid and invalid lines)
- [X] T016 Implement `src/cr10s/config.py`: load TOML from `--config` or `~/.config/cr10s/config.toml` with `tomllib`, apply defaults and validation from [contracts/config.md](contracts/config.md), apply `CR10S_<SECTION>_<KEY>` env overrides, return a frozen dataclass. Never log the `ntfy_topic` value
- [X] T017 Create `config.example.toml` at the repo root from [contracts/config.md](contracts/config.md), with placeholder values only
- [X] T018 Implement `src/cr10s/log.py`: `get(tool) -> Logger` writes JSON lines to `<log.dir>/<tool>.jsonl`, defaulting to `$XDG_STATE_HOME/cr10s`, then `~/.local/state/cr10s`. It uses the field rules from [contracts/log-record.md](contracts/log-record.md), masks secrets, and writes `run_start`/`run_end` through a context manager. Also mirror human messages to stderr when `-v` is set
- [X] T019 Implement `src/cr10s/prune.py` (`cr10s-log-prune [--dry-run]`) per [contracts/cli.md](contracts/cli.md#cr10s-log-prune---dry-run): age rule, then halving rule, then atomic rewrite. Log `prune_done` with per-file before and after bytes and record counts
- [X] T020 Implement `src/cr10s/cli.py`: the shared argparse parent (`--config`, `--pad`, `-v`, `--json`), the exit-code constants (0 ok, 1 usage/config, 2 unreachable, 3 rejected, 4 local tool, 5 safety refusal), and a `run(main)` wrapper that maps exceptions to those codes and logs them
- [X] T021 Implement `src/cr10s/moonraker.py`: an `httpx.Client` wrapper with `timeout=pad.timeout_s` on every call. Methods: `server_info()`, `query_objects()` (webhooks, print_stats, virtual_sdcard, extruder, heater_bed), `upload()`, `metadata()`, `delete_gcode()`, `list_config()`, `get_config_file()`. There is deliberately no method that starts a print. Log `http_request` and `http_error`
- [X] T022 Implement `src/cr10s/status.py` (`cr10s-status`) per [contracts/cli.md](contracts/cli.md#cr10s-status---watch-once): build a PrinterState dataclass with fields from data-model; print human or `--json` output
- [ ] T023 Run `make check` until T009 to T013 pass. Record "Plan Phase 0 exit" in `docs/build/test-log.md`
- [ ] T024 Write `docs/build/phase-01-pad-network.md`: power the Pad, connect Ethernet, set a DHCP reservation and the hostname `sonicpad.lan`, find the UI and Moonraker ports, add the desktop IP to `[authorization] trusted_clients` in `moonraker.conf` from Fluidd's config editor, and write the exit test
- [ ] T025 Operator: carry out `docs/build/phase-01-pad-network.md`. Record the ports in `docs/decisions.md` under Assumptions, and set `pad.url` in `~/.config/cr10s/config.toml`
- [ ] T026 Prototype research R8 with curl, following steps added to `docs/build/phase-01-pad-network.md`: upload with a wrong `checksum` (expect 422) and check that metadata has `estimated_time`. Record the results in `specs/001-klipper-print-workflow/research.md` under R8, then run `bin/sync-docs`
- [ ] T027 Run `make test-live` (T014). Record "Plan Phase 1 exit" in `docs/build/test-log.md`

**Checkpoint**: tools can read the Pad. Logging and pruning work. User stories can begin.

---

## Phase 3: User Story 1 - Printer runs on the new controller (Priority: P1) 🎯 MVP

**Plan phase**: 2 (bench prototype) + 3 (install in the CR-10S).

**Goal**: the CR-10S moves, heats, homes and prints on the SKR V1.4, five TMC2209s and the Sonic Pad.

**Independent Test**: homing works on all axes; the bed and hot end reach target; the heater fault
drill shuts down within 60 s; a 20 mm cube measures ±0.2 mm on X/Y/Z.

### Bench prototype (Plan Phase 2)

- [ ] T028 [US1] Write `printer/firmware/README.md` with the Klipper build steps from research R2: clone mainline Klipper, run `make menuconfig` (LPC176x; LPC1768 100 MHz, or LPC1769 120 MHz for the Turbo; 16 KiB bootloader; USB), build, copy `out/klipper.bin` to the SD card as `firmware.bin`, and power-cycle. Include a fallback for when the protocol version doesn't match the Pad's Klipper
- [ ] T029 [P] [US1] Save the `make menuconfig` result as `printer/firmware/skr14.config` with a comment header naming the Klipper commit used
- [ ] T030 [P] [US1] Write `docs/wiring/00-power-and-host.md`: a pin table for PSU → SKR `POWER` (VIN) and `HB` input (polarity), the jumper for USB vs VIN power on the SKR, and the SKR USB → Pad. Add a pre-power checklist (continuity, no VIN–GND short, polarity). Generate `docs/wiring/00-power-and-host.png` with `/wiring_diagram`
- [ ] T031 [P] [US1] Write `docs/wiring/01-drivers.md`: TMC2209 UART setup on the SKR V1.4 (jumpers under each socket, DIAG pin removed or cut per decision 9, driver orientation and the EN pin side), and a socket table for XM, YM, ZAM, E0M and E1M (Z1) with UART pins P1.10, P1.9, P1.8, P1.4 and P1.1 from research R1. Generate the PNG with `/wiring_diagram`
- [ ] T032 [US1] Test in `tests/unit/test_printer_cfg.py`: parse every `[section name]` header in `printer/config/*.cfg` and fail on any section type not in `tests/fixtures/klipper_sections.txt`. Build that allowlist from the Klipper Configuration reference (S39), one section type per line (e.g. `mcu`, `printer`, `stepper_x`, `tmc2209`, `extruder`, `heater_bed`, `bltouch`, `bed_mesh`, `z_tilt`, `safe_z_home`, `fan`, `heater_fan`, `filament_switch_sensor`, `filament_motion_sensor`, `adxl345`, `resonance_tester`, `input_shaper`, `gcode_macro`, `delayed_gcode`, `include`, `verify_heater`, `virtual_sdcard`, `pause_resume`, `display_status`). Ignore the `SAVE_CONFIG` block. Skip if no `.cfg` exists yet. Add it to `make check` (Constitution III)
- [ ] T033 [US1] Write `printer/config/printer.cfg` (bench version): `[mcu] serial: /dev/serial/by-id/usb-Klipper_lpc1768_REPLACE`, `[printer] kinematics: cartesian`, `[stepper_x]` only with step P2.2, dir P2.6, enable !P2.1, plus `[tmc2209 stepper_x] uart_pin: P1.10` and `run_current: 0.6`. Standard sections only (Constitution III)
- [ ] T034 [US1] Write `docs/build/phase-02-bench-prototype.md`: a bench mat, fitting drivers, flashing, uploading the custom printer config to the Pad, finding the serial id, and the exit test (MCU connected in Fluidd; `DUMP_TMC STEPPER=stepper_x` reads; `FORCE_MOVE STEPPER=stepper_x DISTANCE=10 VELOCITY=5` turns the motor both ways; then move the motor to each driver socket in turn and repeat `DUMP_TMC` so all 5 sockets are checked)
- [ ] T035 [US1] Operator: carry out `docs/build/phase-02-bench-prototype.md`. Record the MCU serial id in `printer/config/printer.cfg` and the result in `docs/build/test-log.md` (gate: "Pad sees mainline SKR over USB")

### Install in the printer (Plan Phase 3)

- [ ] T036 [P] [US1] Write `docs/wiring/02-motors.md`: CR-10S motor connectors → SKR XM, YM, ZAM, E1M (Z1), E0M. Include coil pairing by multimeter resistance (pairs about 1–4 Ω, open between pairs), the expected direction, and how to fix a reversed motor with the `!` on dir_pin rather than rewiring. Generate the PNG
- [ ] T037 [P] [US1] Write `docs/wiring/03-endstops.md`: X-STOP P1.29 and Y-STOP P1.28 with the CR-10S switch pinout (signal, GND, and 5 V if used), and note that Z-STOP P1.27 is left empty after US2. Generate the PNG
- [ ] T038 [P] [US1] Write `docs/wiring/04-heaters-thermistors.md`: hot end heater HE0 (P2.7), thermistor TH0 (P0.24), bed HB (P2.5), and bed thermistor TB (P0.25). Include wire gauge and screw torque notes for the bed, and an explicit mains/12 V warning. Generate the PNG
- [ ] T039 [P] [US1] Write `docs/wiring/05-fans.md`: part fan FAN0 (P2.3); hot end fan on always-on 12 V for now, with HE1 (P2.4) set aside for US8; and the polarity check. Generate the PNG
- [ ] T040 [US1] Expand `printer/config/printer.cfg` to the full motion config: `[stepper_x|y|z|z1]` with pins from research R1, rotation_distance per Klipper's Rotation Distance doc (CR-10S defaults: X/Y 40 with GT2 20T, Z 8 per lead screw), position_max X 300, Y 300, Z 400, `[tmc2209 …]` for all 5 with run_current from the motor spec, `[extruder]` (stock CR-10S extruder rotation_distance as a starting value, marked "calibrate"), `[heater_bed]`, `[fan]`, `[verify_heater extruder]` and `[verify_heater heater_bed]` at default settings, `max_temp` 260 for the extruder and 110 for the bed. Temporarily keep the stock Z switch on P1.27 for `[stepper_z]` until US2
- [ ] T041 [P] [US1] Write `printer/config/macros.cfg`: `START_PRINT BED= EXTRUDER=` and `END_PRINT` (heaters off, motors off, park), using standard gcode_macro only. Add `[include macros.cfg]` to `printer/config/printer.cfg`
- [ ] T042 [US1] Write `docs/build/phase-03-install-controller.md`: photograph and label every stock connector, remove the stock board, mount the SKR (printed mount, standoffs), wire it per `docs/wiring/00` to `05`, run the full pre-power checklist, power on with a hand on the switch, and then the exit test (`QUERY_ENDSTOPS` with each switch pressed and released; each axis jogs 10 mm ±0.5 mm the right way; `PID_CALIBRATE HEATER=extruder TARGET=210` and `HEATER=heater_bed TARGET=60`, then `SAVE_CONFIG`; heater fault drills: (a) unplug TH0 during heat-up, shutdown ≤ 60 s; (b) power off, unplug HE0, power on, `M104 S200`, expect "not heating at expected rate" ≤ 60 s; (c) same with HB unplugged and `M140 S60`, ≤ 120 s; reconnect each with power off; print a 20 mm cube and measure it to ±0.2 mm)
- [ ] T043 [US1] Operator: carry out `docs/build/phase-03-install-controller.md`. Copy the post-`SAVE_CONFIG` `printer.cfg` from the Pad (Fluidd download) into `printer/config/printer.cfg` and commit it
- [ ] T044 [US1] Gate: record the US1 results in `docs/build/test-log.md` (endstops, jog, PID, heater drills a/b/c, cube dimensions). PASS is required before US2. Also record `II ✔` (pre-power checklist done, no safety bypass) and `VI ✔` (`pre-commit run -a` clean) in the Constitution column

**Checkpoint**: the printer works on Klipper. This is the MVP.

---

## Phase 4: User Story 2 - Automatic bed leveling and gantry squaring (Priority: P2)

**Plan phase**: 4. **Depends on**: US1 gate.

**Goal**: the CR Touch homes Z, `Z_TILT_ADJUST` squares the two Z motors, and a bed mesh is applied.

**Independent Test**: a gantry tilted 1–2 mm is fixed to within 0.05 mm; `PROBE_ACCURACY` range is
under 0.02 mm; all 49 squares of a 7×7 first-layer test stick and each is 0.20 mm ±0.05 mm thick; homing with the probe unplugged stops with an error.

- [ ] T045 [P] [US2] Write `docs/wiring/06-cr-touch.md`: a pin-by-pin table from the CR Touch connector (by function: 5 V, GND, control, GND, signal) to SKR SERVOS (P2.0) and PROBE (P0.10), with an adapter cable note and a warning from research R5 never to trust wire colors. Add a multimeter checklist before power-on. Generate the PNG
- [ ] T046 [P] [US2] Write the probe mount notes in `docs/build/phase-04-cr-touch.md` (part, link, how to measure the X/Y offsets)
- [ ] T047 [US2] Update `printer/config/printer.cfg`: `[bltouch] sensor_pin: ^P0.10`, `control_pin: P2.0`, offsets (placeholders marked "measure"); `[stepper_z] endstop_pin: probe:z_virtual_endstop` and remove `position_endstop`; `[safe_z_home]` at the bed center (150, 150); `[z_tilt]` with `z_positions` at the two lead screws and `points` near each side; `[bed_mesh]` mesh_min/max inside the probe reach, `probe_count: 7,7`
- [ ] T048 [US2] Update `printer/config/macros.cfg`: `START_PRINT` runs `G28`, then `Z_TILT_ADJUST`, then `G28 Z`, then `BED_MESH_CALIBRATE`
- [ ] T049 [US2] Complete `docs/build/phase-04-cr-touch.md`: mount the probe, remove the Z switch, wire it per `docs/wiring/06`, then prototype steps before any homing (`BLTOUCH_DEBUG COMMAND=pin_down`, then `pin_up`, `QUERY_PROBE` triggered/open, a finger under the nozzle on the first `G28 Z`), `PROBE_CALIBRATE` for z_offset, and the exit test from the Independent Test above
- [ ] T050 [US2] Operator: carry out `docs/build/phase-04-cr-touch.md`. Commit the updated `printer/config/printer.cfg`
- [ ] T051 [US2] Gate: record the US2 results (tilt before/after, PROBE_ACCURACY range, first-layer photo, unplugged-probe result) in `docs/build/test-log.md`. Also record `II ✔` (pre-power checklist done, no safety bypass) and `VI ✔` (`pre-commit run -a` clean) in the Constitution column

**Checkpoint**: US1 and US2 pass.

---

## Phase 5: User Story 3 - Filament problems pause the print (Priority: P3)

**Plan phase**: 5. **Depends on**: US1 gate (and US2 for real prints).

**Goal**: SFS V2 run-out and jam detection pause and park the print, and the print can be resumed.

**Independent Test**: cutting the filament or holding it still mid-print pauses and parks; resume
shows no shift; no false trips in 3 homing and load cycles.

- [ ] T052 [P] [US3] Write `docs/wiring/07-sfs-v2.md` from the BTT SFS V2.0 manual (research R6, S18): connector pinout by function (switch signal, encoder signal, supply, GND), switch → E0DET (P1.26), encoder → E1DET (P1.25), and the supply voltage check against the manual. Warn that wire colors change between batches. End with the pre-power checklist: continuity per pin, no short between supply and GND, supply voltage measured at the connector with the board on and the device unplugged. Generate the PNG
- [ ] T053 [US3] Update `printer/config/printer.cfg`: `[filament_switch_sensor sfs_switch] switch_pin: ^P1.26`, `pause_on_runout: True`; `[filament_motion_sensor sfs_motion] switch_pin: ^P1.25`, `detection_length: 10`, `extruder: extruder`, `pause_on_runout: True`. Start both in monitor mode (`pause_on_runout: False`) for the prototype step
- [ ] T054 [US3] Update `printer/config/macros.cfg`: `PAUSE`/`RESUME` overrides with a park position (X 10, Y 290, Z +10 mm, retract 1 mm); `SFS_ENABLE`/`SFS_DISABLE` using `SET_FILAMENT_SENSOR SENSOR=sfs_motion ENABLE=1/0`; call `SFS_DISABLE` at Klipper start (`[delayed_gcode]`) and in `END_PRINT`, and `SFS_ENABLE` at the end of `START_PRINT`
- [ ] T055 [US3] Write `docs/build/phase-05-sfs.md`: print the mount (S17), install it, wire it, run the pre-power checklist from `docs/wiring/07-sfs-v2.md` before power-on, run monitor mode on a test print and check the `runout_gcode` log lines, switch to `pause_on_runout: True`, then the exit test from the Independent Test above
- [ ] T056 [US3] Operator: carry out `docs/build/phase-05-sfs.md`. Commit `printer/config/`
- [ ] T057 [US3] Gate: record the US3 results in `docs/build/test-log.md`. Also record `II ✔` (pre-power checklist done, no safety bypass) and `VI ✔` (`pre-commit run -a` clean) in the Constitution column

**Checkpoint**: US1 to US3 pass.

---

## Phase 6: User Story 4 - Fast prints without ringing (Priority: P4)

**Plan phase**: 8. **Depends on**: US1 and US2 gates. The plan places it after US6 so long tuning
prints are watched. Either order meets the constitution.

**Goal**: input shaping is calibrated and applied, allowing at least 1.5× speed without extra ringing.

**Independent Test**: a ringing tower at ≥1.5× the old speed shows no more ringing than the untuned
baseline, and the reference part prints ≥30 % faster (SC-005).

- [ ] T058 [US4] Operator: print the baseline ringing tower and the reference part at the current speed. Record the print time and photos in `docs/build/test-log.md` (the SC-005 baseline)
- [ ] T059 [P] [US4] Write `docs/wiring/08-accelerometer.md`: how the Sonic Pad kit G-sensor connects to the Pad (research R4, verify), plus the fallback ADXL345 → SKR EXP2 SPI pin table (EXP2 pins from research S2) and the USB RP2040 option. End with the pre-power checklist: continuity per pin, no short between supply and GND, supply voltage measured at the connector with the board on and the device unplugged. Generate the PNG
- [ ] T060 [US4] Update `printer/config/printer.cfg`: `[adxl345]` per the Pad's G-sensor (verify the `cs_pin`/chip naming during the prototype) and `[resonance_tester] accel_chip: adxl345`, `probe_points: 150, 150, 20`. Leave `[input_shaper]` empty until calibration
- [ ] T061 [US4] Write `docs/build/phase-08-input-shaping.md`: mount the sensor on the hot end, run the pre-power checklist from `docs/wiring/08-accelerometer.md` before power-on, `ACCELEROMETER_QUERY` (values change when tapped), `SHAPER_CALIBRATE AXIS=X`, move it to the bed, `SHAPER_CALIBRATE AXIS=Y`, `SAVE_CONFIG`, retune `max_accel` per Klipper Resonance Compensation (S42), then the exit test
- [ ] T062 [US4] Operator: carry out `docs/build/phase-08-input-shaping.md`. Commit `printer/config/printer.cfg` with the `[input_shaper]` values
- [ ] T063 [US4] Gate: record the US4 results (shaper type and freq for X and Y, tower photos, reference time vs T058) in `docs/build/test-log.md`. Also record `II ✔` (pre-power checklist done, no safety bypass) and `VI ✔` (`pre-commit run -a` clean) in the Constitution column

**Checkpoint**: US1 to US4 pass.

---

## Phase 7: User Story 5 - One command from design to printer (Priority: P5)

**Plan phase**: 6 (upload code from Plan Phase 1). **Depends on**: Foundational. Code and
integration tests need no hardware and can run in parallel with US1 to US4. The live exit test needs
the US1 gate.

**Goal**: `make upload` in a model repo exports, slices and uploads with a checksum, and never starts
the print.

**Independent Test**: from a clean checkout, `make upload` finishes in < 3 min, the file shows in
Fluidd with time and filament, the print state stays `standby`, and a second run skips export and
slicing.

### Tests (write first, must fail)

- [ ] T064 [P] [US5] Contract tests in `tests/integration/test_upload.py`: the upload form has `root=gcodes`, `print=false` and a `checksum` equal to the file's SHA-256, and never `print=true`. 201 gives exit 0 and prints the remote path plus time/filament. 422 gives exit 3 and event `checksum_mismatch`. Unreachable or hang gives exit 2 in ≤ 15 s. Non-`.gcode` or empty file gives exit 1. Checksum-ignored fallback (research R8): a size/metadata mismatch gives exit 3. No partial file: when the fake server drops the connection mid-body, its file store gains nothing; uploading over an existing name with a bad checksum leaves the old file's bytes unchanged. `/printer/print/start` is never hit
- [ ] T065 [P] [US5] Unit tests in `tests/unit/test_slice.py`: pull `Metadata/plate_1.gcode` out of a fixture `.gcode.3mf`; exit 4 when no plate G-code is present; use `xvfb-run` only when `$DISPLAY` is unset; version mismatch against `printer/profiles/VERSION` warns, and exits 4 with `--strict`. Mock the `orca-slicer` subprocess
- [ ] T066 [P] [US5] Unit tests in `tests/unit/test_export.py`: builds the openscad command with `-D` overrides; logs `export_ok`; non-zero openscad exit gives exit 4 and `export_failed` with stderr tail; timeout gives exit 4. Mock the subprocess
- [ ] T067 [P] [US5] Integration test in `tests/integration/test_model_template.py`: in a temp copy of `templates/model-project/` with a fixture `cube.scad`, a fake `openscad`/`orca-slicer` on `PATH` writing known outputs, and the fake Moonraker, `make upload` uploads once; a second `make upload` runs neither fake tool (mtime-based); all log records share one `run_id`, and they include `export_ok`, `slice_ok` and `upload_ok`
- [ ] T068 [P] [US5] Live test in `tests/live/test_upload_live.py`: upload `tests/fixtures/cube.gcode` to `path=cr10s-live-test`, check the metadata, upload again to the same name with a wrong `checksum` and check that the stored file's size and metadata are unchanged, delete the file, and assert `print_stats.state == "standby"` throughout

### Implementation

- [ ] T069 [P] [US5] Create `tests/fixtures/cube.scad` (a 20 mm cube) and `tests/fixtures/cube.gcode` (a tiny valid Klipper-flavor G-code with slicer header comments for metadata), plus `tests/fixtures/cube.gcode.3mf` (a zip with `Metadata/plate_1.gcode`)
- [ ] T070 [US5] Implement `src/cr10s/upload.py` (`cr10s-upload FILE.gcode [--path DIR] [--name NAME]`) per [contracts/cli.md](contracts/cli.md#cr10s-upload-filegcode---path-dir---name-name). `print=false` is a hard-coded constant with no override, and the PrintFile fields come from data-model. After a 201, fetch metadata, and run the fallback size check if the Pad ignored the checksum
- [ ] T071 [US5] Implement `src/cr10s/export.py` (`cr10s-export MODEL.scad -o OUT.stl [-D name=value ...]`) per [contracts/cli.md](contracts/cli.md#cr10s-export-modelscad--o-outstl--d-namevalue-): run openscad with a 300 s timeout, log `export_ok`/`export_failed`, exit 4 on failure
- [ ] T072 [US5] Implement `src/cr10s/slice.py` (`cr10s-slice`) per [contracts/cli.md](contracts/cli.md#cr10s-slice-modelstl---profiles-dir---filament-name--o-outgcode): build the command from research R7, run it with a timeout (default 300 s), pull the plate G-code into `-o`, and log `slice_ok`/`slice_failed` with the stderr tail
- [ ] T073 [US5] Create `templates/model-project/Makefile` (targets `stl` calling `cr10s-export`, `gcode`, `upload`, `clean`, per [contracts/cli.md](contracts/cli.md#model-project-makefile-templatesmodel-projectmakefile)), with `CR10S_RUN_ID ?= $(shell uuidgen)` exported, `NAME ?= $(notdir $(CURDIR))`, and `PROFILES ?=` the installed repo's `printer/profiles`. Also create `templates/model-project/.gitignore` (`build/`), `templates/model-project/README.md`, and `templates/model-project/NOTES.md` (tuning log)
- [ ] T074 [US5] Prototype research R7: write `docs/build/phase-06-slicing.md` with steps to install the OrcaSlicer AppImage as `~/.local/bin/orca-slicer`, record `orca-slicer --help` output into `printer/profiles/CLI-NOTES.md`, and do one manual CLI slice. Update `src/cr10s/slice.py` flags to match, and record the version in `printer/profiles/VERSION`
- [ ] T075 [US5] Operator: in the OrcaSlicer GUI, build the CR-10S machine, process and PLA profiles (G-code flavor Klipper, bed 300×300, height 400, start G-code `START_PRINT BED=[bed_temperature_initial_layer_single] EXTRUDER=[nozzle_temperature_initial_layer]`, end `END_PRINT`), and export them to `printer/profiles/machine.json`, `process.json` and `pla.json`. Add the Pad as a Physical Printer for GUI uploads with "start print after upload" off
- [ ] T076 [US5] Complete `docs/build/phase-06-slicing.md` exit test: clean-checkout timing (< 3 min), skip on the second run, CLI vs GUI time/filament within 2 %, corrupt-upload and unreachable-host failures with log records
- [ ] T077 [US5] Operator: carry out the exit test. Record it in `docs/build/test-log.md` (gate US5). Also record `II ✔` (pre-power checklist done, no safety bypass) and `VI ✔` (`pre-commit run -a` clean) in the Constitution column

**Checkpoint**: design to Pad in one command, with no auto-start.

---

## Phase 8: User Story 6 - Know what the printer is doing while away from it (Priority: P6)

**Plan phase**: 7. **Depends on**: Foundational for code. The live test needs the US1 gate (and US3
for the filament-trip alert).

**Goal**: the desktop watcher alerts the desktop and phone on every print and host state change.

**Independent Test**: start, pause, resume, cancel and complete a short print, and unplug the SKR USB.
Each event reaches both targets in ≤ 30 s. After a reboot and login the watcher is running.

### Tests (write first, must fail)

- [ ] T078 [P] [US6] Unit tests in `tests/unit/test_watch_state.py`, a table-driven test of every transition in the [data-model watcher state machine](data-model.md#watcher-state-machine): print_started, print_paused (includes the filament message when `print_stats.message` has it), print_resumed, print_complete, print_cancelled, print_error, klipper_down, klipper_ready, host_unreachable after `unreachable_after` (3) failed polls and only once, host_recovered, print_stalled after `stall_min` (15) unchanged-progress minutes and only once per stall, one `watch_started` summary on the first snapshot (no burst of alerts), and one `watch_resumed` summary (no change alerts) when the gap since the last poll is more than `3 × poll_s`
- [ ] T079 [P] [US6] Unit tests in `tests/unit/test_notify.py`: notify-send is called with title/body/urgency; the ntfy POST to `<ntfy_url>/<topic>` has `Title`, `Priority` (`high` for error/klipper_down/unreachable/paused, otherwise `default`) and `Tags`; one target raising does not stop the other and logs `notify_failed`; an empty topic means ntfy is skipped; the topic never appears in log records
- [ ] T080 [P] [US6] Integration test in `tests/integration/test_watch.py`: run `cr10s-watch` against fake-Moonraker scripted snapshots with `poll_s=2` and stub notifiers. Check the alert sequence and timing (each alert within 2 polls of its change), and that SIGTERM logs `watch_stopped` and exits 0

### Implementation

- [ ] T081 [P] [US6] Implement `src/cr10s/notify.py`: an `Alert` dataclass (fields from data-model), `DesktopNotifier` (`notify-send -u <urgency> -a cr10s`), `NtfyNotifier` (httpx POST, 10 s timeout), and `send_all(alert, notifiers)` that sends to each target on its own and logs `alert_sent`/`notify_failed`
- [ ] T082 [US6] Implement `src/cr10s/watch.py` (`cr10s-watch [--once] [--no-desktop] [--no-ntfy]`): a pure `transition(prev, curr, clock) -> list[Alert]` function (tested by T078), a poll loop at `watch.poll_s` that measures the gap since the last poll (monotonic clock) and passes it to `transition` for `watch_resumed`, a SIGTERM handler, and `state_change` log records
- [ ] T083 [P] [US6] Create `systemd/cr10s-watch.service` (user unit: `ExecStart=%h/.local/bin/cr10s-watch`, `Restart=on-failure`, `RestartSec=10`, `WantedBy=default.target`)
- [ ] T084 [P] [US6] Create `systemd/cr10s-log-prune.service` (oneshot) and `systemd/cr10s-log-prune.timer` (`OnCalendar=daily`, `Persistent=true`)
- [ ] T085 [US6] Implement the `install` target in the root `Makefile`: `uv tool install --force .`, copy `systemd/*` to `~/.config/systemd/user/`, `systemctl --user daemon-reload`, `enable --now cr10s-watch.service cr10s-log-prune.timer`. Add an `uninstall` target too. Add `bin/install-check` (bash, shellcheck-clean) that prints the unit status
- [ ] T086 [US6] Write `docs/build/phase-07-monitoring.md`: subscribe to a random ntfy topic on the phone, set it in `config.toml`, `make install`, then the exit test from the Independent Test above, including the reboot/login check
- [ ] T087 [US6] Operator: carry out the exit test. Record each event's delay for desktop and phone in `docs/build/test-log.md` (SC-003: 10 events, 100 % within 30 s). Also record `II ✔` (pre-power checklist done, no safety bypass) and `VI ✔` (`pre-commit run -a` clean) in the Constitution column

**Checkpoint**: long prints are watched.

---

## Phase 9: User Story 7 - Troubleshoot and recover (Priority: P7)

**Plan phase**: 9. **Depends on**: US1 gate (live backup). Logging and pruning were done in
Foundational.

**Goal**: config backups to git, a proven restore to a fresh host, and logs that find faults fast.

**Independent Test**: a macro change on the Pad becomes a single-file commit; config restored to a
fresh host passes the US1 cube; a planted failed upload is found in the logs in < 5 min.

### Tests (write first, must fail)

- [ ] T088 [P] [US7] Integration tests in `tests/integration/test_backup.py` against the fake Moonraker config root and a temp git repo: files are downloaded to `printer/config/` except `*.bkp` and logs; no diff gives `backup_no_change` and no commit; a diff gives one commit listing the changed files; a planted secret makes the gitleaks step fail with exit 5 and no commit (stub gitleaks as a script on `PATH`); `--logs` writes `klippy.log` under the state dir and never into the repo
- [ ] T089 [P] [US7] Unit test in `tests/unit/test_log_query.py`: the `jq` examples in [contracts/log-record.md](contracts/log-record.md) give the expected records on fixture logs (skip if `jq` is missing)

### Implementation

- [ ] T090 [US7] Implement `src/cr10s/backup.py` (`cr10s-backup [--no-commit] [--logs]`) per [contracts/cli.md](contracts/cli.md#cr10s-backup---no-commit---logs): list and download the config root, write it to `printer/config/`, `git add printer/config`, run `gitleaks protect --staged`, and commit with message `backup: <files>` plus the attribution footer
- [ ] T091 [US7] Write `docs/build/phase-09-backup-restore.md`: run a backup after a macro change, then a restore drill (upload `printer/config/*` to a fresh Pad custom-printer profile or a test Pi running mainline Klipper, set the MCU serial, restart, run the US1 cube test), then a log drill (plant a bad-checksum upload, find it with `jq` by `event`)
- [ ] T092 [US7] Write `docs/troubleshooting.md`: where each log lives (desktop `~/.local/state/cr10s/*.jsonl`, Pad `klippy.log` and `moonraker.log` via `cr10s-backup --logs`), common events and what they mean, MCU disconnect checks (USB cable, power, `dmesg` on the Pad via SSH if allowed by decision 3), and how to hand logs to Claude
- [ ] T093 [US7] Operator: carry out `docs/build/phase-09-backup-restore.md`. Record it in `docs/build/test-log.md` (gate US7, SC-007, SC-010). Also record `II ✔` (pre-power checklist done, no safety bypass) and `VI ✔` (`pre-commit run -a` clean) in the Constitution column

**Checkpoint**: core feature complete (US1 to US7).

---

## Phase 10: User Story 8 - Later hardware and software upgrades (Priority: P8)

**Plan phases**: 11 to 16. **Depends on**: core sign-off (T108). Each sub-phase is independent and
ends by re-running the US1 cube test plus its own test.

- [ ] T094 [P] [US8] Write `docs/build/phase-11-webcam.md`: plug the USB webcam into the Pad, set up the webcam in Fluidd (and the Pad's camera settings), take a time-lapse; exit test: live view and a time-lapse file
- [ ] T095 [P] [US8] Write `docs/build/phase-12-pei.md`: fit the PEI sheet, `PROBE_CALIBRATE` for a new z_offset, `SAVE_CONFIG`; exit test: first layer sticks, part releases when cool
- [ ] T096 [P] [US8] Write `docs/build/phase-13-bmg.md` and update `printer/config/printer.cfg` `[extruder]` with `rotation_distance` and `gear_ratio: 50:17` per Klipper Rotation Distance (S44), then a pressure advance tower per S43; exit test: 100 mm extrude gives 100 ± 1 mm
- [ ] T097 [P] [US8] Write `docs/wiring/09-hotend-5015.md` (5015 blower on FAN0 P2.3, hot end fan moved to HE1 P2.4 as `[heater_fan hotend_fan] heater_pin: P2.4`, `heater_temp: 50`) and `docs/build/phase-14-hotend-5015.md` (Micro Swiss install, duct print, raise `max_temp` to 285 only after checking the thermistor type, `PID_CALIBRATE` at 240); exit test: holds 260 °C ±2 °C for 10 min, a 20°–70° overhang test (5° steps) prints a clean overhang at least 10° steeper than the stock-fan baseline from before the swap. End with the pre-power checklist: continuity per pin, no short between supply and GND, supply voltage measured at the connector with the board on and the device unplugged. Generate the PNG
- [ ] T098 [P] [US8] Write `docs/build/phase-15-mainline-host.md`: full `cr10s-backup` first, follow the community mainline route (S35), install Mainsail, restore `printer/config/`, rebuild the MCU firmware to match the new host Klipper version (`printer/firmware/README.md`), and add the Moonraker `[notifier]` as an optional extra; exit test: US1 to US7 tests pass, and Mainsail serves the UI
- [ ] T099 [P] [US8] Add a FreeCAD target to `templates/model-project/Makefile` (`STL from $(NAME).FCStd via freecadcmd export.py`) and `templates/model-project/export.py` (`Mesh.export` per S55, verified on the installed FreeCAD), plus a test in `tests/integration/test_model_template.py` with a fake `freecadcmd`; exit test: a FreeCAD part goes through the US5 test
- [ ] T100 [US8] Operator: carry out each of T094 to T099 when the parts are on hand. Record each gate in `docs/build/test-log.md`. Also record `II ✔` (pre-power checklist done, no safety bypass) and `VI ✔` (`pre-commit run -a` clean) in the Constitution column

---

## Phase 11: Polish & Cross-Cutting Concerns

- [ ] T101 [P] Write `docs/build/README.md`: an index of build phases with links, the order, the gates, and the safety rules (Constitution II) at the top
- [ ] T102 [P] Write `docs/wiring/README.md`: an index of wiring docs, the full SKR V1.4 pin-use table (research R1), and a list of free pins
- [ ] T103 [P] Update `README.md`: status badge to `in progress` or `core complete`, Quick Start (`uv sync`, `make check`, `make install`, `config.example.toml`), and the project tree with `src/`, `printer/`, `templates/` and `systemd/`
- [ ] T104 [P] Update `CLAUDE.md`: commands (`make check`, `make test-live`, `uv run pytest tests/unit/test_prune.py::test_age_rule` for a single test, `bin/sync-docs`), and the package layout
- [ ] T105 Run `bin/sync-docs` and commit `docs/prd.md` and `docs/plan.md` if the masters changed
- [ ] T106 Run the [quickstart.md](quickstart.md) sections 1 to 5 end to end. Fix anything that diverges
- [ ] T107 Run `pre-commit run -a` and `gitleaks detect` on the full history; record the result in `docs/build/test-log.md` (SC-009)
- [ ] T108 Core sign-off (Plan Phase 10): re-run the US1 to US7 exit tests, check SC-001 to SC-010 in `docs/build/test-log.md`, and tag the release `git tag -a v1.0-core`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: needs Setup. Blocks every story.
- **US1 to US4 (hardware)**: in order, each gated on the one before (US4 needs US1 and US2 only).
- **US5 and US6 (software)**: code and integration tests need only Foundational, so they can run in
  parallel with the hardware stories. Their live exit tests need the US1 gate (and US3 for the
  filament alert).
- **US7**: code needs Foundational. The live restore drill needs the US1 gate.
- **US8**: needs core sign-off (T108).
- **Polish**: T101 to T107 any time after their inputs exist. T108 last, before US8.

### User Story Dependencies

```text
Setup → Foundational ─┬─> US1 ─> US2 ─> US3
                      │          └────> US4
                      ├─> US5 (code) ──> US5 live (after US1)
                      ├─> US6 (code) ──> US6 live (after US1, US3)
                      └─> US7 (code) ──> US7 drill (after US1)
US1..US7 gates ─> T108 core sign-off ─> US8 (T094..T100, any order)
```

Suggested physical order (matches plan.md): Foundational → US1 → US2 → US3 → US5 live →
US6 live → US4 → US7 → T108 → US8.

### Within Each User Story

- Tests are written first and must fail. Then the code, then the guides, then the operator steps,
  then the gate.
- Wiring docs come before the build guide that uses them. The pre-power checklist comes before any
  power-on.

### Parallel Opportunities

- Setup: T003, T004 and T005.
- Foundational tests: T009 to T014 together. T015 alongside them.
- US1: wiring docs T030 and T031, then T036 to T039, all [P].
- While the operator does US1 to US4 hardware, Claude can build US5, US6 and US7 code (T064 to
  T073, T078 to T085, T088 to T090).
- US8 sub-phases T094 to T099 are fully independent.

---

## Parallel Example: User Story 6

```bash
# Tests first, in parallel:
Task: "Unit tests for state machine in tests/unit/test_watch_state.py"
Task: "Unit tests for notifiers in tests/unit/test_notify.py"
Task: "Integration test for watcher in tests/integration/test_watch.py"

# Then independent implementation files:
Task: "Implement notifiers in src/cr10s/notify.py"
Task: "Create systemd/cr10s-watch.service"
Task: "Create systemd/cr10s-log-prune.{service,timer}"
```

## Parallel Example: User Story 1 (docs while the bench is set up)

```bash
Task: "Write docs/wiring/02-motors.md + PNG"
Task: "Write docs/wiring/03-endstops.md + PNG"
Task: "Write docs/wiring/04-heaters-thermistors.md + PNG"
Task: "Write docs/wiring/05-fans.md + PNG"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup, then Phase 2 Foundational (the Pad on the network, tools read it, logging works).
1. Phase 3 US1: bench prototype, then install, then gate T044.
1. **Stop and validate**: the printer prints a ±0.2 mm cube on Klipper. The old SD-card workflow
   still works, because the Pad's touchscreen can print from USB.

### Incremental Delivery

1. US2 (leveling), then US3 (filament): each one is gated.
1. US5 and US6 (built during US1 to US3) go live: the new workflow plus alerts.
1. US4 tuning, then US7 drills, then T108 tags `v1.0-core`.
1. US8 upgrades as parts arrive.

### Solo Operator + Claude

- Claude: docs, config, code and tests (tasks without the "Operator:" prefix).
- Operator: physical steps and gate sign-offs. Claude reads `docs/build/test-log.md` to know what
  passed.

---

## Notes

- [P] = different files, no unfinished dependencies.
- Make a `.bak` copy before editing an existing file (user rule). `*.bak*` is git-ignored.
- Commit after each task or logical group. Never commit `config.toml`, `.env*` or firmware binaries.
- Every `docs/build/phase-NN-*.md` follows `docs/build/_template.md` (photo checkpoints, risky steps and recovery, exit test).
- Every `docs/wiring/*.md` ends with a pre-power checklist, and every build guide that wires something runs it before power-on (Constitution II).
- Never add a code path that sends `print=true` or calls `/printer/print/start` (Constitution II).
