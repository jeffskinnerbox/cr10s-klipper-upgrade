# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Early stage: docs + planning only. No code, build, or tests yet. Not yet a git repo (`input/my-prompts.md` 5th prompt: create repo, README via `/readme-wizard`, push to GitHub, then `docs/prd.md` + `docs/plan.md`).

## Goal

Upgrade a Creality CR-10S (300x300x400mm, 12V PSU, dual-Z already fitted) to Klipper, and replace the manual CAD -> Cura -> SD-card workflow with a scripted, monitored one. Work = hardware assembly/wiring + software config + Python/Bash automation + integration tests, built in testable phases.

Hardware in hand: Creality Sonic Pad (Klipper host), BTT SKR V1.4 mainboard, TMC2209 drivers, CR Touch, BTT SFS V2 filament sensor, ADXL345.

## Architecture (target)

- **Desktop Ubuntu** = design + build + automation. FreeCAD/OpenSCAD -> STL (headless), OrcaSlicer CLI -> G-code, `curl` upload to Moonraker. Never in the print path.
- **Sonic Pad** = print + watch. Klipper host, Moonraker API, Mainsail/Fluidd UI, webcam. Stores G-code; nothing should exist only on the Pad (`printer.cfg` backed up to git).
- **SKR V1.4** runs mainline Klipper MCU firmware; CR-10S+SKR is a "custom printer" for the Pad (no official Creality support).
- Per-project git repo + `Makefile`: `make upload` = export STL -> slice -> upload with sha256 checksum, `print=false`. Starting a print is always a manual human gate (clear bed).
- Monitoring: `pad-watch` polls `printer/objects/query?webhooks&virtual_sdcard&print_stats`, alerts on state changes (incl. Klipper disconnect, filament trip). Should run on always-on host, not desktop.
- Logging required for troubleshooting, with periodic pruning (e.g. >6 months, or drop oldest half at 50MB).

## Known Risks / Unverified (check before relying on)

- Pad's Klipper/Moonraker are old Creality forks; newer Moonraker features (notifier, Apprise) may be missing.
- Moonraker port on Pad: 7125 default vs 7128 reported. UI at `http://<pad-ip>` no port.
- Mainsail availability on Pad unverified (stock UI is Fluidd).
- OrcaSlicer CLI flags vary by release; may need `xvfb-run`; output may be `.gcode.3mf`.
- Sensorless homing (DIAG pins) can interfere with SFS on same MCU.
- CR Touch wiring differs from BLTouch; wrong wiring can fry it.
- Keep config portable: standard Klipper sections only, no Creality-specific macros (fallback host: BTT Pad 7 / Pi).

## Layout

- `input/` — author's source material: `my-vision.md` (upgrade vision, parts, sources), `new-workflow.md` (researched workflow, phased plan, open questions), `my-prompts.md` (prompt history / next-step instructions).
- `docs/` — older reference/link collections (CR-10S, Cura/Slic3r notes, Sonic Pad/SKR upgrade).

## Conventions

- Markdown linted with `markdownlint-cli2` using `.markdownlint-cli2.jsonc` (symlink to dotfiles; `fix: true`, line length 300). Existing docs number ordered lists `1.` for every item. Run: `markdownlint-cli2 "**/*.md"`.
- Docs use reference-style links (`[text][NN]`) with definitions at file bottom.
- `*.bak*` and `secret*` files are git-ignored; never commit secrets (Moonraker tokens, Telegram bot tokens, etc.).
- Code language: Python or Bash.
