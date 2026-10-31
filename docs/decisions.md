# Decisions

Decisions from the grill-me session on 2026-10-30, before writing the PRD and plan.

| #   | Question                         | Decision                                                                                                       |
| :-- | :------------------------------- | :------------------------------------------------------------------------------------------------------------- |
| 1   | Where spec-kit files live        | Master copies in `specs/001-…/` (`spec.md`, `plan.md`). Copied to `docs/prd.md` and `docs/plan.md` by a sync script. |
| 2   | Klipper host software on the Pad | Stock Creality fork first. Move to Debian/mainline in a later phase.                                           |
| 3   | Root SSH on the Pad              | Only if needed. Plan uses the web/API first, with SSH as a fallback for debugging.                             |
| 4   | Where `pad-watch` runs           | Desktop, as a `systemd --user` service. Accept gaps when the desktop sleeps.                                   |
| 5   | Alert targets                    | Desktop `notify-send` plus phone push via ntfy. Topic is kept in a git-ignored `.env`.                         |
| 6   | CAD tool                         | OpenSCAD first. FreeCAD headless export in a later phase.                                                      |
| 7   | Repo layout                      | This repo holds the guides, config backups, profiles, tools and tests. Models live in their own repos.        |
| 8   | Hardware scope                   | Core: Sonic Pad, SKR V1.4, TMC2209, CR Touch, BTT SFS V2, ADXL345. Extras, in later phases: USB webcam, BMG extruder, Micro Swiss hot end + 5015 fan, PEI sheet. |
| 9   | X/Y/Z homing                     | Mechanical X/Y endstops, CR Touch homes Z. DIAG jumpers removed, no sensorless homing.                         |
| 10  | Dual-Z wiring                    | Independent drivers, with Z1 on the E1 driver socket (5 TMC2209s). Enables `Z_TILT_ADJUST`.                    |
| 11  | Logging                          | JSON lines in `~/.local/state/cr10s/`. A daily prune drops entries older than 180 days, then the oldest half if still over 50 MB. |
| 12  | Integration testing              | pytest against a local fake Moonraker. Opt-in `--live` smoke tests against the Pad; these never start a print. |
| 13  | Code stack                       | Python package managed by uv (httpx, pytest, ruff). Thin Bash glue checked by shellcheck.                      |
| 14  | Remote access / power            | LAN only, no smart plug. VPN and smart plug go on the "later" list.                                           |
| 15  | Wiring docs                      | One file per subsystem: pinout table plus a PNG from `/wiring_diagram`. Photo checkpoints and a multimeter check before power-on. |
| 16  | Web UI                           | Fluidd (stock on the Pad) now. Mainsail when the Pad moves to mainline.                                       |

## Assumptions

- The desktop runs Ubuntu with Python 3.12+ and `uv` installed.
- 5 TMC2209 drivers are on hand, to be confirmed in the first hardware phase.
- Pad ports (confirmed 2026-10-31): Moonraker on 7125 (`http://<pad-ip>:7125`), UI on 80. Moonraker version reports `?` (Creality fork).
- Pad IP is 192.168.1.152 from DHCP. The Pad UI has no static-IP setting. The router reservation (Verizon G3100, target 192.168.1.205) is deferred: **TODO before the first long print and before `cr10s-watch` runs unattended.**
- With no MCU attached, Klipper reports `shutdown` ("Lost communication with MCU") and `/printer/objects/query` still returns HTTP 200, so no `/server/info` fallback is needed in `status.poll()`.
