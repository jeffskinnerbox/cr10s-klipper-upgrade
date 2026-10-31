<!--
Sync Impact Report
- Version change: template (unversioned) → 1.0.0
- Principles: added I–VI (all new)
- Added sections: Core Principles, Constraints, Development Workflow, Governance
- Removed sections: none
- Templates: plan/spec/tasks templates read this file at runtime; no edits needed
- Deferred TODOs: none
-->

# cr10s-klipper-upgrade Constitution

## Core Principles

### I. Phased and Testable Build

- Work MUST be split into phases. Each phase MUST end with a written pass/fail test.
- A phase MUST NOT start until the test of the phase before it passes.
- Hardware, wiring, config and code MUST advance together, so each phase turns on
  a function that can be tested.

Rationale: a fault found right after the change that caused it is cheap to fix.

### II. Safety First (NON-NEGOTIABLE)

- Mains power MUST be unplugged before any wiring work.
- Before first power-on after wiring, the builder MUST do a multimeter check for
  continuity and shorts, and polarity on power leads.
- Klipper heater protection (`verify_heater`) MUST stay enabled. It MUST be tested
  before any unattended heat-up.
- No script or slicer setting MAY start a print. Upload sets `print=false`.
  A person starts each print after clearing the bed.

Rationale: heaters, mains and moving parts can cause fire or injury.

### III. Portable Configuration

- Printer config MUST use standard Klipper sections only. Creality-specific macros
  are NOT allowed.
- Nothing MAY exist only on the Sonic Pad. `printer.cfg`, `moonraker.conf` and macros
  MUST be backed up to git.
- The Sonic Pad is a host that can be replaced. Moving to a Pi or BTT Pad 7 MUST NOT
  need any rewiring.

Rationale: the Sonic Pad is discontinued, and its firmware is a fork.

### IV. Test-Backed Automation

- Automation code MUST be Python, packaged with `uv`, tested with `pytest` and
  linted with `ruff`. Bash glue MUST pass `shellcheck`.
- Integration tests MUST run against a local fake Moonraker and need no hardware.
- Live tests against the Pad MUST be opt-in (`--live`) and MUST NOT start a print.

Rationale: scripts that move files to a machine that heats metal must be trusted.

### V. Observable

- Every workflow step (export, slice, upload, status, watch, prune) MUST write
  JSON-lines log records: time, level, tool, event and details.
- Logs MUST be readable by a person with `grep`/`jq` and parseable by Claude.
- Retention: entries older than 180 days MUST be removed. If a log is still over
  50 MB, its oldest half MUST be removed.

Rationale: print faults are often intermittent, such as MCU disconnects, so the
trail must exist when they happen.

### VI. No Secrets in Git

- Secrets such as the ntfy topic, tokens and passwords MUST live in a git-ignored
  `.env` or the user config dir.
- A pre-commit secret scan MUST block commits that contain credentials.
- Docs and examples MUST use placeholders, never real values.

Rationale: the repo is public.

## Constraints

- Desktop: Ubuntu. It runs CAD, slicing, automation and `pad-watch` as a
  `systemd --user` service.
- Host: Creality Sonic Pad running the stock Creality Klipper/Moonraker fork,
  with the Fluidd UI. Mainline Klipper and Mainsail come in a later phase.
- MCU: BTT SKR V1.4 running mainline Klipper firmware built on the desktop.
- Network: LAN only. No Internet exposure of the Pad, no VPN and no smart plug in
  the current scope.
- Root SSH on the Pad is used only when a task cannot be done through the web UI
  or API.

## Development Workflow

- spec-kit artifacts in `specs/` are the master copies. `docs/prd.md` and
  `docs/plan.md` are synced copies made by a script and are never edited by hand.
- Decisions are recorded in `docs/decisions.md`.
- Markdown MUST pass `markdownlint-cli2` with the repo config.
- Before each file edit, a `.bak` copy is made. `*.bak*` files are git-ignored.

## Governance

- This constitution overrides other practice docs. Plans and task lists MUST
  include a Constitution Check against Principles I–VI.
- Amendments: edit this file through `/speckit-constitution`, bump the version and
  record why in the commit message.
- Versioning: MAJOR when a principle is removed or redefined, MINOR when one is
  added or expanded, PATCH for wording.
- Review: each phase's test sign-off confirms that Principles II and VI were met.

**Version**: 1.0.0 | **Ratified**: 2026-10-30 | **Last Amended**: 2026-10-30
