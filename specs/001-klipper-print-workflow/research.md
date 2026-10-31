# Research: CR-10S Klipper Upgrade and Automated Print Workflow

Phase 0 output for [plan.md](plan.md). Researched 2026-10-30.
**(verify)** marks a fact that could not be confirmed online. The plan tests each one in a
prototype step. Source keys such as [S1] refer to the Sources list in [plan.md](plan.md#sources).

## R1. SKR V1.4 pin map for this build

- **Decision**: use the pins from Klipper's `generic-bigtreetech-skr-v1.4.cfg` [S1], cross-checked
  against Marlin's `pins_BTT_SKR_V1_4.h` [S2]:

  | Function            | Board port   | MCU pin  | Klipper section                        |
  | :------------------ | :----------- | :------- | :------------------------------------- |
  | X step/dir/en       | XM driver    | P2.2 / P2.6 / !P2.1   | `[stepper_x]`                 |
  | Y step/dir/en       | YM driver    | P0.19 / P0.20 / !P2.8 | `[stepper_y]`                 |
  | Z step/dir/en       | ZAM driver   | P0.22 / !P2.11 / !P0.21 | `[stepper_z]`               |
  | Z1 step/dir/en      | E1M driver   | P1.15 / P1.14 / !P1.16 | `[stepper_z1]`               |
  | E0 step/dir/en      | E0M driver   | P2.13 / !P0.11 / !P2.12 | `[extruder]`                |
  | TMC UART X/Y/Z/E0/E1| driver socket| P1.10 / P1.9 / P1.8 / P1.4 / P1.1 | `[tmc2209 …] uart_pin` |
  | X endstop           | X-STOP       | P1.29    | `endstop_pin: P1.29` (polarity in test) |
  | Y endstop           | Y-STOP       | P1.28    | `endstop_pin: P1.28`                   |
  | Z (CR Touch)        | PROBE/SERVOS | P0.10 / P2.0 | `[bltouch] sensor_pin: ^P0.10`, `control_pin: P2.0` |
  | SFS switch (runout) | E0DET        | P1.26    | `[filament_switch_sensor]`             |
  | SFS encoder (motion)| E1DET        | P1.25    | `[filament_motion_sensor]`             |
  | Hot end heater      | HE0          | P2.7     | `[extruder] heater_pin`                |
  | Hot end thermistor  | TH0          | P0.24    | `[extruder] sensor_pin`                |
  | Bed heater          | HB           | P2.5     | `[heater_bed] heater_pin`              |
  | Bed thermistor      | TB           | P0.25    | `[heater_bed] sensor_pin`              |
  | Part fan            | FAN0         | P2.3     | `[fan]`                                |
  | Spare PWM (later 5015 / hot end fan) | HE1 | P2.4 | `[heater_fan]` or `[fan_generic]` |

  Z1 on E1M starts with the same direction as Z (`!P1.14`). The T040 jog test confirms all
  directions.

- **Rationale**: the Klipper config is the upstream reference. The Marlin header confirms the
  servo (P2.0) and probe (P0.10) pins, which the Klipper generic config leaves out.
- **Alternatives**: Z motors in parallel on the ZAM/ZBM header, rejected by decision 10.
  Sensorless homing on DIAG pins, rejected by decision 9 and by the SFS conflict warning [S8].
- **(verify)**: endstop polarity (`!` or `^`) depends on the CR-10S switch wiring. Phase 3 checks
  it with `QUERY_ENDSTOPS`.

## R2. Klipper MCU firmware for SKR V1.4

- **Decision**: build mainline Klipper on the desktop. `make menuconfig` settings: LPC176x,
  LPC1768 at 100 MHz (LPC1769 at 120 MHz for the Turbo), 16 KiB bootloader, USB communication.
  Copy `out/klipper.bin` to the SD card as `firmware.bin` and power-cycle the board [S1, S3].
- **Rationale**: the board's own SD bootloader means no programmer is needed, and the SD card
  can always reflash the board, even if the build was bad.
- **Alternatives**: the Pad's built-in "user-defined printer compilation" [S6]. It covers
  Creality boards and makes no config file, so it is not used.
- **(verify)**: whether the stock Pad Klipper fork talks to the mainline MCU protocol version.
  Klipper host and MCU versions should match. Phase 2 checks this on the bench. Fallback: build the
  MCU firmware from the Pad's own Klipper source tree, found by `git log` over SSH (decision 3
  allows SSH when needed) or from CrealityTech's GitHub [S5].

## R3. Sonic Pad as host for a custom board

- **Decision**: use the Pad's "custom printer" path. Upload our own `printer.cfg` and point
  `[mcu] serial` at the SKR's `/dev/serial/by-id/usb-Klipper_lpc1768_…`.
- **Rationale**: Creality supports only listed printers. For custom boards it points to its
  custom-printer manual and paid help [S6, S7]. The community steps (build, flash, find serial,
  edit `printer.cfg`, restart) match normal Klipper setup [S9].
- **(verify)**: that the stock Pad finds an LPC1768 board over USB. No source found shows this
  exact pairing. Klipper's forum does not support the Pad's fork [S10, S11], so plan for
  community-only help. Phase 2 tests this on the bench before anything is installed in the printer.

## R4. Accelerometer (ADXL345) on the Sonic Pad

- **Decision**: use the G-sensor that came with the Pad kit, plugged into the Pad as Creality
  intends. Fallback: wire an ADXL345 to the SKR's SPI on the EXP2 header, or buy a USB
  (RP2040) ADXL board.
- **Rationale**: the Pad has built-in input-shaper support. Klipper's resonance docs show the
  Pi-host form [S12], which needs changes for the Pad [S13].
- **(verify)**: the Pad's `[adxl345]` section and `cs_pin`. Phase 8 prototype: run
  `ACCELEROMETER_QUERY` before mounting.

## R5. CR Touch on SKR V1.4

- **Decision**: configure it as `[bltouch]` with `sensor_pin: ^P0.10` and `control_pin: P2.0`.
  Use `[safe_z_home]`, plus `[bed_mesh]` and `[z_tilt]`. Remove the Z-stop switch.
- **Rationale**: Klipper treats the CR Touch as a BLTouch and needs a pull-up on the sensor
  pin [S14]. The `BLTOUCH_DEBUG` pin_down/pin_up tests come before any homing [S14, S15].
- **Risk**: CR Touch and BLTouch wiring orders differ, and wrong wiring has destroyed probes
  [S16]. The wiring guide uses a pin-by-pin table checked with a multimeter, never wire colors.

## R6. BTT SFS V2 filament sensor

- **Decision**: switch output on E0DET (P1.26) as `[filament_switch_sensor]`, and encoder output
  on E1DET (P1.25) as `[filament_motion_sensor]` with `detection_length: 10`. Both use
  `pause_on_runout: True`. Enable/disable macros turn the motion sensor on only while printing
  [S8, S17].
- **Rationale**: the Voron guide recommends 10 mm to avoid false triggers [S8]. BTT rates
  detection at 2.88 mm [S18]. Disabling the motion sensor outside prints stops false pauses
  during homing and loading.
- **(verify)**: connector pinout and wire colors change between batches [S19]. Use the BTT
  manual [S18]. The 5 V vs 3.3 V supply is checked in Phase 5.

## R7. OrcaSlicer CLI

- **Decision**: `xvfb-run orca-slicer --load-settings "machine.json;process.json"
  --load-filaments "pla.json" --arrange 1 --slice 0 --outputdir build --export-3mf part.gcode.3mf part.stl`.
  The `orca_slice` wrapper then takes `Metadata/plate_1.gcode` out of the 3MF to make a plain
  `.gcode` [S20, S21].
- **Rationale**: the CLI exports a `.gcode.3mf` archive, with the G-code inside it [S21].
  Pulling it out keeps the Pad's file viewer and metadata parsing working. Flags change between
  releases [S20], so the wrapper checks the version and fails loudly on unknown output.
- **Alternatives**: PrusaSlicer CLI (`--export-gcode`), which has a stable CLI but is not the
  chosen slicer. Kept as a fallback.
- **(verify)**: the exact flags on the installed version (`orca-slicer --help`). Whether the
  AppImage needs `xvfb-run`. Phase 6 prototype.

## R8. Moonraker upload and status

- **Decision**: `POST /server/files/upload` (multipart) with `root=gcodes`, `path=<project>`,
  `checksum=<sha256>` and `print=false`. A 201 response means success, and a 422 means checksum
  mismatch. The `path` folder is created if missing. `GET /server/files/metadata?filename=…`
  returns `estimated_time` and `filament_total` [S22].
  Status: `GET /printer/objects/query?webhooks&print_stats&virtual_sdcard&extruder&heater_bed`
  [S23].
- **Rationale**: plain HTTP, easy to fake in tests.
- **(verify)**: the Pad's old Moonraker fork may not support `checksum`, or may use another
  port (7125 or 7128). Phase 1 checks this. If `checksum` is ignored, the upload tool re-reads
  the file's size and metadata after upload as a weaker check.

## R9. Notifications

- **Decision**: desktop alerts with `notify-send` (libnotify). Phone alerts with an HTTP POST
  to `https://ntfy.sh/<topic>`, using `Title`, `Priority` and `Tags` headers [S24]. The topic
  lives in `~/.config/cr10s/config.toml` or `.env` and is never committed. The topic acts as a
  password [S24].
- **Alternatives**: Moonraker `[notifier]`/Apprise on the Pad. It may be missing from the
  old fork [S25] and is left for the mainline phase. `moonraker-telegram-bot` [S26] needs a
  token and is more setup.

## R10. Logging and retention

- **Decision**: a shared `cr10s.log` module writes JSON lines to
  `$XDG_STATE_HOME/cr10s/<tool>.jsonl` (default `~/.local/state/cr10s/`). `cr10s-log-prune`
  runs from a daily `systemd --user` timer. It first drops records older than 180 days, then, if a
  file is still over 50 MB, drops its oldest half. Files are rewritten safely (write to a temp
  file, then `os.replace`).
- **Rationale**: grep/jq friendly, and Claude can parse it. `logrotate` can't prune
  record-by-record by age, so a small tool does it [S27].

## R11. Packaging, testing, secrets

- **Decision**: Python ≥3.12, a `uv` project with console scripts [S28]. `httpx` for HTTP
  [S29]. `pytest` plus `pytest-httpserver` for the fake Moonraker [S30]. `ruff` for lint/format
  [S31]. `shellcheck` for Bash [S32]. `pre-commit` with `gitleaks` for secret scanning
  [S33, S34]. Standard-library `tomllib` for config.
- **Rationale**: few dependencies, and runs offline in CI or on a laptop.
- **Alternatives**: `requests` (no timeouts by default, no HTTP/2, both minor), `responses`
  mocks (doesn't run a real socket, so it misses multipart edge cases).

## R12. Mainline host later (Debian on the Pad, Mainsail)

- **Decision**: a later phase. Evaluate the community "Sonic Pad – Mainline Klipper" route
  [S35]. Mainsail docs cover OrcaSlicer upload [S36].
- **Rationale**: decision 2. The core build first runs on the stock fork.
