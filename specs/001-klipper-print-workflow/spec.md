# Feature Specification: CR-10S Klipper Upgrade and Automated Print Workflow

**Feature Branch**: `main` (no feature branch; single-owner repo)

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "CR-10S Klipper upgrade and automated print workflow. Upgrade a Creality
CR-10S (300x300x400, 12V, dual-Z) from the stock 8-bit board to a BTT SKR V1.4 with 5x TMC2209, run by
a Creality Sonic Pad, plus CR Touch, independent dual-Z, BTT SFS V2, ADXL345 and mechanical X/Y
endstops; later a webcam, BMG extruder, all-metal hot end + 5015 fan, PEI sheet, mainline host
software and FreeCAD export. Desktop design -> STL -> slice -> upload, with a manual start gate,
monitoring and alerts, logging with retention, config backups, assembly and wiring guides, and
tests. No secrets in git. LAN only."

Decisions behind this spec are in [docs/decisions.md](../../docs/decisions.md).

## Overview

### Actors

- **Builder/Operator**: the owner. Assembles and wires the printer, designs parts, starts prints.
- **Desktop**: the Ubuntu computer. Designs, slices, uploads, watches and alerts.
- **Printer host**: the Sonic Pad. Stores print files, runs the motion software, serves the web UI.
- **Printer**: the CR-10S frame, motors, heaters and sensors, driven by the new mainboard.

### Target Workflow

This is the full workflow the project delivers, from design to finished part.

1. **Design.** The operator edits a parametric model in a model repo on the desktop and commits it.
1. **Export.** One command turns the model into a mesh file in a git-ignored build folder.
1. **Slice.** The same command slices the mesh with the shared, version-controlled printer,
   process and filament profiles, and makes a print file.
1. **Upload.** The same command sends the print file to the printer host and verifies its checksum.
   The upload never starts a print. Steps 2–4 rebuild only what changed.
1. **Review.** In the web UI, the operator checks the preview, estimated time and filament use.
1. **Start (human gate).** The operator clears the bed, checks the filament, and starts the print
   from the web UI or touchscreen.
1. **Monitor.** A watcher on the desktop reports print start, progress milestones, finish, pause,
   error, host or controller disconnect, and filament run-out or jam. Alerts go to the desktop and
   to the operator's phone.
1. **Finish.** The operator gets a "complete" alert, removes the part, and notes any tuning
   change in the model repo.
1. **Record.** Every step writes a structured log record, which old-log cleanup trims.
   Printer config changes are backed up to git.

The old path (mesh -> legacy slicer -> SD card -> walk to the printer) is no longer needed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Printer runs on the new controller (Priority: P1)

The builder replaces the stock 8-bit board with the SKR V1.4 and five TMC2209 drivers, connects it
to the Sonic Pad, and prints a calibration part. All motion, heating, cooling and homing work, and
the safety checks pass.

**Why this priority**: none of the other stories can be done until the printer works on the new
controller.

**Independent Test**: by following the assembly and wiring guides, the builder powers up,
homes all axes, heats the bed and hot end to target, and prints a 20 mm calibration cube that is
within ±0.2 mm on X/Y/Z.

**Acceptance Scenarios**:

1. **Given** the wiring is done and the builder has passed the pre-power multimeter checklist,
   **When** the printer is powered on, **Then** there is no smoke, smell or hot part, and the host
   shows the controller as connected.
1. **Given** the controller is connected, **When** each motor is jogged 10 mm from the web UI,
   **Then** each one moves the right way by 10 mm ±0.5 mm.
1. **Given** a heater thermistor is unplugged or reads wrong, **When** a heat-up is started,
   **Then** the printer shuts the heater off and reports an error within 60 s.
1. **Given** a homed printer, **When** a calibration cube is printed, **Then** it completes and
   measures within ±0.2 mm.

---

### User Story 2 - Automatic bed leveling and gantry squaring (Priority: P2)

The printer probes the bed with the CR Touch, homes Z with it, levels the two Z motors on its own,
and makes up for bed warp during prints.

**Why this priority**: on a 300x300 bed, hand leveling is the biggest source of first-layer
failures.

**Independent Test**: tilt the gantry about 1 mm on purpose, run the leveling routine, and confirm
the tilt is fixed and a full-bed first-layer test print sticks evenly.

**Acceptance Scenarios**:

1. **Given** the gantry is out of level by up to 2 mm, **When** the leveling routine runs,
   **Then** the two sides end within 0.05 mm of each other.
1. **Given** a probed bed mesh, **When** a full-bed first-layer pattern prints, **Then** the
   line height looks even and there are no unstuck areas.
1. **Given** the probe fails to deploy, **When** homing starts, **Then** homing stops with an
   error and the nozzle does not hit the bed.

---

### User Story 3 - Filament problems pause the print (Priority: P3)

The filament sensor pauses the print when filament runs out, breaks or stops moving. The operator
fixes the problem and resumes.

**Why this priority**: on long prints it saves hours and filament, and it pairs with alerts
(US6).

**Independent Test**: cut the filament mid-print, then hold the filament still mid-print. In both
cases the print pauses and can be resumed.

**Acceptance Scenarios**:

1. **Given** a print is running, **When** the filament runs out, **Then** the print pauses within
   10 mm of filament travel and the nozzle parks away from the part.
1. **Given** a print is running, **When** the filament stops moving while the extruder pushes,
   **Then** the print pauses.
1. **Given** a paused print with new filament loaded, **When** the operator resumes,
   **Then** printing continues with no visible layer shift.
1. **Given** the printer is idle or homing, **When** no filament is moving, **Then** no false
   pause or alert happens.

---

### User Story 4 - Fast prints without ringing (Priority: P4)

The builder measures the printer's resonances with the accelerometer and turns on vibration
compensation, so prints run faster with no ringing.

**Why this priority**: this is the main speed and quality gain of the upgrade, but it needs
US1–US2 first.

**Independent Test**: print a ringing test tower before and after tuning, at the same speed.

**Acceptance Scenarios**:

1. **Given** the accelerometer is mounted, **When** the resonance test runs on X and Y,
   **Then** a recommended compensation setting is produced and saved to config.
1. **Given** compensation is on, **When** the ringing tower prints at ≥1.5x the old speed,
   **Then** ringing is the same as or less than the untuned tower at the old speed.

---

### User Story 5 - One command from design to printer (Priority: P5)

The operator runs one command in a model repo. The part is exported, sliced and uploaded to the
printer host, ready to start, with no manual file moves.

**Why this priority**: this is the main workflow goal, replacing the SD-card routine.

**Independent Test**: from a clean checkout of a sample model repo, run the command. The print
file appears on the host with its estimated time and filament use, and no print starts.

**Acceptance Scenarios**:

1. **Given** a sample model, **When** the one command runs, **Then** the print file is on the
   host within 3 minutes and the printer state is still idle.
1. **Given** nothing changed since the last run, **When** the command runs again, **Then** export
   and slicing are skipped.
1. **Given** a file corrupted in transit (checksum mismatch), **When** upload runs, **Then** the
   host rejects the file and the command exits with an error and a log record.
1. **Given** the host can't be reached, **When** upload runs, **Then** the command fails within
   15 s with a clear message, and no partial file is left on the host.
1. **Given** a print file made from the same model and profiles in the slicer's GUI, **When**
   compared with the command's output, **Then** estimated time and filament agree within 2 %.

---

### User Story 6 - Know what the printer is doing while away from it (Priority: P6)

A watcher on the desktop tells the operator when a print starts, finishes, pauses or fails, and
when the host loses the controller, both on the desktop and on the phone.

**Why this priority**: it makes long prints safe to leave without someone watching the screen.

**Independent Test**: start a short print, then pause it, cancel it, and unplug the controller
USB. Each event alerts both targets.

**Acceptance Scenarios**:

1. **Given** the watcher is running, **When** a print starts, completes, pauses, errors or is
   cancelled, **Then** an alert reaches the desktop and phone within 30 s.
1. **Given** a print is running, **When** the host loses the controller, **Then** a "disconnected"
   alert is sent within 30 s.
1. **Given** the host is unreachable, **When** 3 polls in a row fail, **Then** one "host
   unreachable" alert is sent, not one per poll, and one "recovered" alert follows when it's back.
1. **Given** the desktop rebooted, **When** the operator logs in, **Then** the watcher starts by
   itself.
1. **Given** a print shows no progress for 15 minutes while printing, **Then** a "stalled" alert
   is sent.

---

### User Story 7 - Troubleshoot and recover (Priority: P7)

Every workflow step leaves a structured log that the operator or Claude can search. Old logs are
trimmed automatically. Printer config is backed up to git, so the host can be replaced.

**Why this priority**: it supports the other stories. Most of it can be built alongside US5–US6.

**Independent Test**: run the workflow, find a failed upload in the logs by its time and event
name, run cleanup on aged and oversized test logs, and restore config to a fresh host from git.

**Acceptance Scenarios**:

1. **Given** any tool runs, **When** it finishes or fails, **Then** a log record exists with time,
   level, tool, event and details, one record per line.
1. **Given** log records older than 180 days, **When** cleanup runs, **Then** those records are
   removed and newer ones are kept.
1. **Given** a log file over 50 MB after the age rule, **When** cleanup runs, **Then** the oldest
   half of its records is removed.
1. **Given** a config change on the host, **When** backup runs, **Then** the change is committed
   to git with no secrets in it.
1. **Given** a fresh host, **When** config is restored from git, **Then** the printer homes and
   prints with no rewiring.

---

### User Story 8 - Later hardware and software upgrades (Priority: P8)

After the core is stable, the builder adds a USB webcam, BMG extruder, all-metal hot end with 5015
part-cooling fan, and PEI sheet. The builder also moves the host to mainline software with Mainsail,
and adds FreeCAD export to the one-command workflow.

**Why this priority**: each one is an improvement on a printer that already works. Each is
independent and has its own test.

**Independent Test**: each upgrade has its own guide and pass/fail test, for example: webcam view
appears in the UI; extruder pushes 100 mm ±1 mm; hot end holds 260 °C ±2 °C; overhang test better
than baseline; PEI first layer sticks; mainline host passes the US1 test; FreeCAD part goes through
US5.

**Acceptance Scenarios**:

1. **Given** each upgrade is installed by its guide, **When** its test runs, **Then** it passes
   and all US1–US7 tests still pass.

### Edge Cases

- Controller USB disconnect mid-print: print stops safely (heaters off), watcher alerts.
- Desktop sleeps mid-print: print continues on the host. Alerts are missed until the desktop
  wakes, which is accepted (decision 4). The watcher reports the current state on wake.
- Upload while a print is running: allowed. The file is stored and the running print is not
  affected.
- A file with the same name already on the host: it is replaced only after the checksum checks
  out.
- Slicer tool version changes its options: the command fails loudly with a log record. It never
  makes a silent wrong print file.
- Missing alert config (no phone topic): desktop alerts still work. A warning is logged once.
- Phone alert service unreachable: the desktop alert still fires, and the failure is logged.
- Log file is missing or unwritable: the tool still runs and warns on the console.
- Thermal runaway or heater fault: the printer shuts down and an "error" alert is sent.
- Wrong stepper wiring or a reversed motor: found during the jog test before any print.
- Probe (CR Touch) wired wrong: the pre-power check and a probe self-test come before any homing.

## Requirements *(mandatory)*

### Functional Requirements

**Build and wiring guides**

- **FR-001**: The project MUST provide step-by-step assembly instructions for each hardware phase:
  parts and tools, numbered steps, photo checkpoints, and a pass/fail test at the end.
- **FR-002**: The project MUST provide wiring instructions for each subsystem (power, motors,
  endstops, heaters and thermistors, fans, probe, filament sensor, accelerometer, host link). Each
  needs a pin table (board connector/pin → device pin → wire color → config pin name) and a
  diagram.
- **FR-003**: Each wiring guide MUST include a pre-power checklist: continuity, shorts between
  supply rails, supply polarity, and driver orientation and jumpers.
- **FR-004**: The guides MUST name every irreversible or risky step (firmware flash, mains wiring,
  heater wiring) and say how to recover from it.

**Printer function**

- **FR-005**: The printer MUST home X/Y with mechanical endstops and Z with the probe.
- **FR-006**: The printer MUST level the two independent Z motors automatically using the probe.
- **FR-007**: The printer MUST probe a bed mesh and apply it during prints.
- **FR-008**: The printer MUST pause on filament run-out or no filament motion during extrusion,
  park the nozzle, and allow resume.
- **FR-009**: The printer MUST support resonance measurement and apply the resulting vibration
  compensation.
- **FR-010**: Heater fault protection MUST be on for the bed and hot end, and tested before the
  first unattended heat-up.
- **FR-011**: Printer config MUST use only standard, host-portable settings (no vendor-only
  macros), so the host can be replaced with no rewiring.

**Workflow automation**

- **FR-012**: One command MUST export a model, slice it with the version-controlled profiles, and
  upload the result, redoing only steps whose inputs changed.
- **FR-013**: Upload MUST verify file integrity with a checksum and MUST NOT start a print.
- **FR-014**: Each tool MUST return a non-zero exit status and a readable message on failure.
- **FR-015**: A one-shot status command MUST report host state, printer state, current file,
  progress and temperatures.
- **FR-016**: A watcher MUST alert on print start, complete, paused, error, cancelled, controller
  disconnect/shutdown, host unreachable/recovered, filament trip and stalled progress.
- **FR-017**: Alerts MUST go to the desktop and the phone. A failure on one target MUST NOT block
  the other.
- **FR-018**: The watcher MUST start automatically at desktop login and restart after a crash.
- **FR-019**: Tools MUST read host address and alert settings from a local, git-ignored config,
  with documented defaults.

**Logging, backup, safety of data**

- **FR-020**: Every tool MUST write structured, one-record-per-line logs (time, level, tool,
  event, details) to a per-user state directory.
- **FR-021**: Log cleanup MUST run daily. It removes records older than 180 days, then removes
  the oldest half of any log still over 50 MB.
- **FR-022**: A backup command MUST copy host config (printer, host API and macros) into git.
- **FR-023**: The repo MUST block commits that contain secrets, and keep secrets only in git-ignored
  files.

**Testing**

- **FR-024**: Automation MUST have unit tests and integration tests that run with no hardware, against
  a simulated printer host.
- **FR-025**: An opt-in live test suite MUST check the real host without ever starting a print.
- **FR-026**: Each build phase MUST define its test and record pass/fail before the next phase.

**Later phases**

- **FR-027**: The project MUST provide guides and tests for: USB webcam, BMG extruder, all-metal hot
  end + 5015 fan, PEI sheet, host move to mainline software with Mainsail, and FreeCAD export.

### Key Entities

- **Model project**: a model source, a build command and generated outputs. Lives in its own repo.
- **Profile set**: printer, process and filament settings used for slicing. Version-controlled
  here.
- **Print file**: sliced output with checksum, estimated time and filament use. Stored on the host.
- **Printer state**: host connection, controller state, print state, progress and temperatures.
- **Alert**: event type, time, message and the targets it was sent to.
- **Log record**: time, level, tool, event and details.
- **Config backup**: snapshot of host config files in git.
- **Build phase**: steps, wiring, config, test, and pass/fail result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A calibration cube printed on the upgraded printer measures within ±0.2 mm on all axes.
- **SC-002**: From a saved model change to a print file ready on the host takes one command and
  under 3 minutes, with zero manual file moves.
- **SC-003**: Over 10 test events (start, complete, pause, error, cancel, disconnect, filament
  trip), 100 % reach both alert targets within 30 s.
- **SC-004**: 0 prints start without the operator pressing start (checked over all automated and
  live tests).
- **SC-005**: Print time for the reference part drops by ≥30 % with ringing no worse than baseline.
- **SC-006**: Every build phase has a recorded pass for its test before the next phase starts.
- **SC-007**: For any failed workflow run, the operator or Claude can find its cause from the logs
  in under 5 minutes.
- **SC-008**: Log storage never goes over 50 MB per log file, and holds no records older than 180
  days after cleanup.
- **SC-009**: 0 secrets in the public repo history (secret scan clean).
- **SC-010**: Restoring config to a replacement host needs zero wiring changes, and the restored
  printer passes the US1 test.

## Assumptions

- Five TMC2209 drivers are on hand (confirmed in the first hardware phase).
- The CR-10S keeps its 12 V supply, heaters, motors and mechanical X/Y endstops.
- The Sonic Pad runs its stock vendor firmware and web UI (Fluidd) until the mainline phase.
- Root shell access to the Pad is used only when the web UI or API can't do the job.
- Desktop and Pad are on the same LAN. No remote access from outside the home.
- The desktop may sleep. Missed alerts during sleep are accepted.
- Phone alerts use a push service that needs no account. Its topic name is treated as a secret.
- Designs are OpenSCAD first. FreeCAD is a later phase.
- Model repos are separate from this repo and use its tools.
- Parts for later phases (webcam, BMG, hot end, 5015 fan, PEI) will be bought as needed.
