# New 3D Printing Workflow

Research findings for the "Future 3D Printing Environment & Workflow" section of [my-vision.md](my-vision.md).
Researched 2026-10-30.
Items marked **(unverified)** came from one source or were not confirmed against my hardware.

## Recommendation in One Paragraph

Keep the desktop Ubuntu system as the "design and build" machine and the Sonic Pad as the "print and watch" machine.
Put each project in a git repo with a `Makefile`.
`make` exports the STL (OpenSCAD or FreeCAD, headless), slices it with the OrcaSlicer CLI,
and uploads the G-code to the Sonic Pad over Moonraker's HTTP API.
Starting the print stays a human step, because someone has to clear the bed.
Status and alerts come from Moonraker, either through its own notifier or a small watcher script on the desktop.

## 1. Who Does What: Desktop vs Sonic Pad

| Function                    | Desktop Ubuntu                          | Sonic Pad                                     |
| :-------------------------- | :-------------------------------------- | :-------------------------------------------- |
| CAD design                  | FreeCAD / OpenSCAD (GUI and headless)   | none                                          |
| Project files, versioning   | git repos for models and scripts        | `printer.cfg` backed up to git (from desktop) |
| Slicing                     | OrcaSlicer (GUI and CLI)                | none                                          |
| Motion planning, G-code run | none                                    | Klipper host                                  |
| Printer API, file storage   | none (HTTP client only)                 | Moonraker (`gcodes` and `config` roots)       |
| Web UI                      | any browser                             | Mainsail / Fluidd served from the Pad         |
| Camera                      | view in browser                         | USB webcam on the Pad                         |
| Automation, monitoring      | scripts, watcher service, notifications | Moonraker notifier (if the Pad supports it)   |
| Backups                     | git, `rsync` of config                  | source of the config                          |

Design rules:

- The Pad stores nothing that exists only on the Pad.
  G-code is reproducible from the repo.
  `printer.cfg` is copied to git from the desktop.
- The desktop is never in the print path.
  The Pad holds the G-code and runs the job, so a desktop reboot or suspend does not stop a print.
- Anything that needs to survive the print (alerts on failure) should run on the Pad, or on the always-on homelab, not on a desktop that sleeps.

### Connecting the two

- Reach the Pad by IP on the LAN.
  Use a DHCP reservation or a static IP, and add a hostname to `/etc/hosts` or the homelab DNS.
- The Sonic Pad IP is on the touchscreen under Configure > Network.
  A `127.0.0.1` value is the Pad's internal address and is not usable from the desktop. [SimplyPrint][sp-sonic]
- Browse to `http://<pad-ip>` with no port.
  A Creality moderator says no port is needed. [Creality forum][cr-forum]
  SimplyPrint describes the stock UI as Fluidd. **(unverified whether Mainsail is available on the Pad)** [SimplyPrint][sp-sonic]
- Moonraker's default port is 7125, but a Creality forum post cites 7128 for the Pad.
  **Check my own Pad.**
- API access is gated by `[authorization] trusted_clients` in `moonraker.conf`.
  Add the desktop's IP (or the LAN range) so scripts need no token. [Moonraker docs][mr-config]
- SSH to the Pad needs root access turned on in the touchscreen menu (Configure > Other Settings > Advance options > Root account).
  SimplyPrint says this voids the warranty. [SimplyPrint][sp-sonic]
  The Pad's Klipper and Moonraker are old, modified versions, so newer Moonraker features may be missing. [fran6p guide][fran6p]

## 2. Tools for Each Step

CAD -> STL -> G-code -> printed object.

| Step                 | Recommended tool                           | Headless / scriptable?                                   | Notes                                                                                                                           |
| :------------------- | :----------------------------------------- | :------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------ |
| Design               | OpenSCAD (parametric) or FreeCAD           | OpenSCAD: yes. FreeCAD: yes, via Python (`freecadcmd`)   | Keep source files in git. Pick OpenSCAD for code-like parts.                                                                    |
| Export STL           | `openscad -o part.stl part.scad`           | Yes. `-D` overrides parameters, `-q` quiets output       | Pin STL format (ASCII vs binary) in the script. [OpenSCAD man page][scad-man]                                                   |
| Export STL (FreeCAD) | Python: `Mesh.export([obj], "part.stl")`   | Yes, run with `freecadcmd script.py`                     | **(unverified)** examples found were for FreeCAD 0.19. [FreeCAD wiki][fc-wiki]                                                  |
| Slice                | OrcaSlicer                                 | Yes. CLI loads a model, applies settings, runs `--slice` | May need `xvfb-run` on headless Linux. Flags change between releases. [OrcaSlicer CLI wiki][orca-cli], [Printago ref][printago] |
| Check G-code         | Mainsail G-code viewer, Moonraker metadata | Yes. `GET /server/files/metadata`                        | Gives estimated time, filament, layer height. [Moonraker docs][mr-files]                                                        |
| Transfer             | Moonraker HTTP upload (`curl`)             | Yes                                                      | `POST /server/files/upload`. [Moonraker docs][mr-files]                                                                         |
| Start print          | Mainsail / touchscreen (manual) or API     | Yes, but keep it manual                                  | See "Start gate" below.                                                                                                         |
| Monitor              | Mainsail, Moonraker notifier, Telegram bot | Yes                                                      | See section 4.                                                                                                                  |

### Slicer choice

OrcaSlicer, as already decided in `my-vision.md`.
In OrcaSlicer, add a Physical Printer with the Pad's address.
Use host type Octo/Klipper, or the OctoPrint type plus an `[octoprint_compat]` section in `moonraker.conf`.
The Mainsail and Fluidd docs disagree on which one to use, so test both.
Set the G-code flavor to Klipper so Exclude Object commands are emitted. [Mainsail docs][ms-orca], [Fluidd docs][fl-slicer]

The GUI upload button is fine for one-off prints.
The CLI path below is for repeatable builds.

### Start gate

The OrcaSlicer GUI has a "start print after upload" option, and the Moonraker upload call has `print=true`.
Leave both off.
A print that starts the moment a file lands will start on top of the last part if the bed was not cleared.
Upload automatically, start by hand.

## 3. Making It Less Manual

Yes.
Every step above has a command-line form, so a `Makefile` (or shell script) can chain them.

### Project layout

```text
~/src/3d-prints/
  bin/
    pad-upload          # upload G-code to the Pad
    pad-status          # one-shot status check
    pad-watch           # watcher with notifications
  profiles/             # OrcaSlicer machine/process/filament JSON, exported once
  shelf-bracket/
    shelf-bracket.scad  # or .FCStd + export.py
    Makefile
    build/              # generated, git-ignored: .stl and .gcode
```

### Makefile sketch

Untested sketch.
Check the OrcaSlicer flags against the installed version with `orca-slicer --help` first.

```make
.RECIPEPREFIX = >
PAD      ?= http://sonicpad.lan
NAME     := shelf-bracket
PROFILES := ../profiles

build/$(NAME).stl: $(NAME).scad
> mkdir -p build
> openscad -q -o $@ --export-format binstl $<

build/$(NAME).gcode: build/$(NAME).stl
> xvfb-run orca-slicer \
>   --load-settings "$(PROFILES)/machine.json;$(PROFILES)/process.json" \
>   --load-filaments "$(PROFILES)/pla.json" \
>   --slice 1 --outputdir build $<

upload: build/$(NAME).gcode
> ../bin/pad-upload $<

.PHONY: upload
```

`make upload` then rebuilds only what changed.
Editing the `.scad` and running `make upload` takes the part to the Pad with no manual file moves.

### Upload script

Moonraker's upload endpoint is a plain multipart POST.
A checksum makes a corrupted transfer fail instead of printing bad G-code. [Moonraker docs][mr-files]

```bash
#!/usr/bin/env bash
# pad-upload FILE.gcode  -- upload to the Sonic Pad, do NOT start the print
set -euo pipefail
PAD="${PAD:-http://sonicpad.lan}"   # add :port if Moonraker is not on 80
f="$1"
curl --fail -sS -X POST "$PAD/server/files/upload" \
  -F "file=@${f}" \
  -F "root=gcodes" \
  -F "path=auto" \
  -F "checksum=$(sha256sum "$f" | cut -d' ' -f1)" \
  -F "print=false"
```

Per Moonraker, a successful upload returns HTTP 201.
The docs conflict on whether a missing `path` folder is created, so test that on the Pad.

### Optional extras

- **Parameter sweeps and variants.**
  OpenSCAD `-D name=value` builds size variants from one source.
  `scadbatch` (pre-release) drives this from CSV or JSON. [PyPI][scadbatch]
- **Auto-build on save.**
  `entr` or `watchexec` on the `.scad` file runs `make` when it changes.
  Use it for the STL only, so a half-edited file does not slice and upload on every keystroke.
- **Git hooks / CI.**
  A pre-commit hook can run `make` to catch a model that no longer exports or slices.
- **Desktop shortcut.**
  A `.desktop` launcher or shell alias for `pad-status` and `pad-upload`.
- **LLM/MCP wrappers.**
  Third-party OrcaSlicer MCP servers exist (e.g., `orca-mcp`).
  They are useful as a reference for CLI usage, but I would not depend on them. [orca-mcp][orca-mcp]

## 4. Monitoring and Status

### Built-in views (no work)

- Mainsail / Fluidd dashboard from any browser: temperatures, progress, G-code console, webcam, job history.
- Pad touchscreen.

### Polling status from scripts

Moonraker exposes status over HTTP and a JSON-RPC websocket.
Poll every 1-2 s at most, or subscribe on the websocket. [Moonraker docs][mr-api]

```bash
curl -s "$PAD/printer/objects/query?webhooks&virtual_sdcard&print_stats"
```

- `webhooks.state` should be `ready`.
- `print_stats.state` is one of `standby`, `printing`, `paused`, `error`, `complete`.
- `virtual_sdcard.progress` is 0-1.

A `pad-watch` script can poll this, detect state changes, and send a message.
Run it as a `systemd --user` service on the desktop, or better on an always-on homelab host.

### Push notifications

| Option                           | Where it runs      | What you get                                                                                         | Caveat                                                                                                                              |
| :------------------------------- | :----------------- | :--------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------- |
| Moonraker `[notifier]` + Apprise | on the Pad         | Alerts on events (start, complete, error) to ntfy, Telegram, Discord, email and others               | **(unverified)** The Pad's Moonraker is old and modified. It may lack notifier support or Apprise. [Moonraker integrations][mr-int] |
| `moonraker-telegram-bot`         | homelab host       | Progress at set intervals, webcam pictures, time-lapse, `/status` `/pause` `/resume`, emergency stop | Needs a Telegram bot. Runs off the Pad, so the Pad's age matters less. [GitHub][tg-bot]                                             |
| Home Assistant (REST)            | homelab host       | Failed/complete alerts, dashboards, automations (lights, plugs)                                      | No official integration. Community REST approach only. [GitHub][ha-moon]                                                            |
| Own `pad-watch` script           | desktop or homelab | Whatever I write: `notify-send`, `ntfy`, email                                                       | I maintain it.                                                                                                                      |

Recommendation:
start with `pad-watch` posting to [ntfy](https://ntfy.sh/) or `notify-send` (simple, no extra accounts).
If a homelab host exists, run `moonraker-telegram-bot` there for webcam snapshots and remote pause.
Try the Moonraker `[notifier]` only after confirming the Pad supports it.

### What to alert on

- Print started, complete, paused, error.
- Klipper disconnected or shutdown (watch `webhooks.state`).
  This matters because [my-vision.md](my-vision.md) notes users report MCU disconnects on the Pad.
- Filament sensor trip (the Smart Filament Sensor pauses the print).
- Optional: no state change for N minutes while `printing`.

### Safety

- Never leave a print unwatched without a way to stop it.
  A pause/cancel path from the phone (Telegram bot or Mainsail on VPN) is the minimum.
- Consider a smart plug on the printer with Moonraker's power control.
  Moonraker lists power control as a feature. [my-vision.md](my-vision.md)
- Do not expose the Pad's web UI to the Internet.
  Use a VPN (WireGuard) for remote access.
  Services like OctoEverywhere exist for the Pad, but they send traffic through a third party. [OctoEverywhere][octo]

## 5. The New Workflow

```text
 DESKTOP UBUNTU                                   SONIC PAD (LAN)
 ----------------                                 ----------------
 1. Design   FreeCAD / OpenSCAD  (git repo)
        |
 2. make     openscad -> build/part.stl
        |
 3. make     orca-slicer CLI -> build/part.gcode
        |
 4. make upload  curl POST /server/files/upload ----> Moonraker stores G-code
        |                                              (gcodes/auto/part.gcode)
 5. Review   Mainsail: preview, time, filament <----- metadata + G-code viewer
        |
 6. HUMAN GATE: clear bed, check filament, press Start (Mainsail or touchscreen)
        |                                              Klipper -> SKR 1.4 -> printer
 7. Monitor  pad-watch / Telegram bot / Mainsail <---- Moonraker status + webcam
        |
 8. Done     notification; remove part; log result in repo
```

Step by step:

1. **Design.**
   Edit the model in the project repo.
   Commit.
2. **Export STL.**
   `make` runs `openscad` (or `freecadcmd export.py`).
   Output goes to `build/`, which is git-ignored.
3. **Slice.**
   `make` runs the OrcaSlicer CLI with the shared profiles in `profiles/`.
4. **Upload.**
   `make upload` pushes the G-code to the Pad with a checksum.
   It does not start the print.
5. **Review.**
   Open Mainsail, find the file, check the preview, estimated time, and filament use.
6. **Start (manual gate).**
   Clear the bed, confirm filament, then start from Mainsail or the touchscreen.
7. **Monitor.**
   The watcher or bot reports progress and problems.
   The webcam is available in Mainsail.
8. **Finish.**
   Notification arrives.
   Remove the part, and note any tuning change in the project's `NOTES.md`.

The current manual path (STL -> Cura -> SD card -> walk to printer) is replaced by steps 2-4, which are one command.

## 6. Phased Implementation Plan

Each phase is testable on its own.
Phases 2 and 5 need the CR-10S printing; the rest need only the Pad on the network.

### Phase 1 - Connectivity

- Give the Pad a fixed IP or DHCP reservation and a hostname.
- Find the real Moonraker port and UI port.
- Add the desktop to `trusted_clients`.
- **Test:** `curl http://<pad>/server/info` from the desktop returns JSON with `klippy_state`.

### Phase 2 - Manual upload through OrcaSlicer

- Add the Pad as a Physical Printer in OrcaSlicer; set G-code flavor to Klipper.
- Slice one small test part in the GUI and upload it.
- **Test:** the file appears in Mainsail/Fluidd; a print starts from there and completes.

### Phase 3 - Scripted upload

- Write `pad-upload` and `pad-status`.
- **Test:** upload an existing `.gcode`; checksum mismatch test (edit the file after hashing) returns an error.

### Phase 4 - Scripted slice and export

- Export OrcaSlicer machine/process/filament profiles to `profiles/`.
- Write the `Makefile` for one OpenSCAD part.
- **Test:** `make upload` from a clean checkout produces a G-code that matches the GUI-sliced one (compare time and filament in Moonraker metadata).
- Repeat once for a FreeCAD part with `freecadcmd`.

### Phase 5 - Monitoring

- Write `pad-watch` with desktop or ntfy notifications.
- **Test:** start a short print; see started and complete alerts. Cancel a print; see the alert.
- Add `moonraker-telegram-bot` if a homelab host is available.

### Phase 6 - Hardening

- Back up `printer.cfg` and `moonraker.conf` to git (`scp` or `rsync` from the Pad, or fetch with `GET /server/files/...` on the `config` root).
- Document the recovery path (fallback to the BTT Pad 7 in `my-vision.md`).
- Optional: VPN for remote access, smart plug for power cut.

## 7. Risks and Unverified Items

- **Sonic Pad is old and modified.**
  Its Klipper and Moonraker are older Creality forks.
  Features in current Moonraker docs (notifiers, Apprise, newer endpoints) may be missing. [fran6p guide][fran6p]
- **Custom board.**
  The CR-10S with an SKR 1.4 is a custom printer for the Pad.
  I found no guide for that path (see `my-vision.md`).
  The workflow above assumes the Pad's Moonraker works normally once Klipper runs.
- **Mainsail on the Pad.**
  `my-vision.md` says the plan is to host Mainsail on the Pad.
  The sources I found only describe Fluidd on the stock Pad.
  Fluidd gives the same function if Mainsail cannot be installed.
- **OrcaSlicer CLI.**
  Flags change between releases, and some builds want a display (`xvfb-run`).
  One source says the output may be `.gcode.3mf` rather than plain `.gcode` depending on flags.
  Test with the installed version. [Printago ref][printago]
- **FreeCAD headless export.**
  I found only a FreeCAD 0.19-era example.
  Verify with the installed version.
- **Docs conflict.**
  Moonraker docs disagree on whether a missing upload `path` is created.

## Unresolved Questions

- Mainsail or Fluidd on the Pad: is Mainsail installable, or settle for Fluidd?
- Real Moonraker/UI ports on my Pad?
- Is there an always-on homelab host for `pad-watch` and the Telegram bot?
- Notification target: phone (ntfy/Telegram), desktop only, or email?
- FreeCAD or OpenSCAD as the main CAD tool? (Decides how much `freecadcmd` scripting is needed.)
- Is a smart plug / power cut wanted for the printer?
- Remote access wanted (VPN) or LAN only?
- Should `printer.cfg` live in the same git repo as the models, or its own?
- Allow root SSH on the Pad (voids warranty), or avoid it and use only the web/API paths?

## Sources

[ms-orca]: https://docs.mainsail.xyz/slicers/orcaslicer/
[fl-slicer]: https://docs.fluidd.xyz/features/slicer-uploads/
[mr-files]: https://moonraker.readthedocs.io/en/latest/external_api/file_manager/
[mr-api]: https://moonraker.readthedocs.io/en/latest/external_api/introduction/
[mr-config]: https://moonraker.readthedocs.io/en/latest/configuration/
[mr-int]: https://moonraker.readthedocs.io/en/stable/external_api/integrations/
[tg-bot]: https://github.com/nlef/moonraker-telegram-bot
[ha-moon]: https://github.com/fryc88/HomeAssistant-Moonraker-for-Klipper
[orca-cli]: https://www.orcaslicer.com/wiki/cli/cli_mode
[printago]: https://printago.io/blog/orca-slicer-cli-reference
[orca-mcp]: https://pypi.org/project/orca-mcp/
[scad-man]: https://man.archlinux.org/man/openscad.1.en
[scadbatch]: https://pypi.org/project/scadbatch/
[fc-wiki]: https://wiki.freecad.org/Mesh_Export
[sp-sonic]: https://simplyprint.io/setup-guide/methods/sonic-pad.md
[cr-forum]: https://forum.creality.com/t/cura-cant-send-wireless-print-files-to-sonicpad/5712
[fran6p]: https://github.com/fran6p/SonicPad/blob/main/Obico/obico-spad.md
[octo]: https://blog.octoeverywhere.com/remote-access-for-the-creality-sonic-pad/
