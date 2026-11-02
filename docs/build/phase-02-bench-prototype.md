# Phase 02: Bench prototype

## Purpose

Prove on the bench that the Sonic Pad's Klipper talks to a mainline-firmware SKR V1.4 over USB, and that all five TMC2209 sockets work, before anything is installed in the printer.
This is user story US1, plan Phase 2 (tasks T034 and T035).
It settles the open question in research R2 and R3: does the Pad's Klipper fork speak to a mainline MCU?

The printer is not touched. The old board stays installed. One stepper motor is used, moved from socket to socket.

## Parts and tools

- Parts:
  - 1 SKR V1.4 Turbo with the firmware from `printer/firmware/README.md` already built
  - 5 TMC2209 drivers, heatsinks fitted
  - 1 stepper motor (a spare, or a CR-10S motor taken off the machine and left free on the bench)
  - 12 V PSU, with the wiring from `docs/wiring/00-power-and-host.md`
  - 1 microSD card (FAT32, 32 GB or smaller)
  - 1 USB cable, SKR to the Pad `USB1`
  - A non-conductive bench mat (a silicone or anti-static mat, or cardboard)
- Tools: multimeter, small pliers, desktop with a browser.

## Risky steps and recovery

| Step | Risk | Undo or recover |
| :-- | :-- | :-- |
| 2 | A driver in backwards or a wrong jumper destroys the driver or the board. | Follow `docs/wiring/01-drivers.md`. Check each socket against the silkscreen before you insert the driver. |
| 3 | A bad flash leaves no USB device. | Reflash from the SD card, as often as needed. The bootloader always runs. See the troubleshooting table in `printer/firmware/README.md`. |
| 5 | A wrong `printer.cfg` stops Klipper. | Download the Pad's original `printer.cfg` first (step 5) and paste it back. |
| 7 | Connecting or removing a motor or driver while powered can destroy the driver. | Power off first, every time. Unplug the PSU, wait 10 seconds, then change the part. |
| 8 | `FORCE_MOVE` has no limits and ignores endstops. | Use 10 mm moves on a free motor only. Nothing else is connected. |

## Steps

Do the steps in order. Write the result of each in `docs/build/test-log.md` (Notes column).

1. Set up the bench. Put the SKR on the mat. Do the pre-power checklist in `docs/wiring/00-power-and-host.md`. Take its three photos.
   📷 The SKR on the mat, PSU unplugged, USB removed.
2. Fit the drivers. Fit a driver in socket `XM` only, following `docs/wiring/01-drivers.md` (UART jumpers, `DIAG` pin removed, orientation). Put the other four drivers aside.
   📷 The `XM` socket from above, with the driver in.
3. Flash the firmware from the SD card, following `printer/firmware/README.md` step 2. Check that the file was renamed `FIRMWARE.CUR`.
   📷 The SD card contents on the desktop, showing `FIRMWARE.CUR`.
4. Connect the SKR to the Pad.
   Connect the USB cable from the SKR to the Pad `USB1`.
   Set the USB jumper as `docs/wiring/00-power-and-host.md` says for "board on the PSU and linked to the Pad".
   Connect the PSU `+V` and `-V` to `POWER`, and the motor to `XM`, with the PSU unplugged. Then plug the PSU in.
   📷 The whole bench: PSU, SKR, motor, USB to the Pad.
5. Put the config on the Pad.
   1. Open Fluidd at `http://<pad-ip>`. Go to the Configuration tab (the name may differ).
   2. **Download the existing `printer.cfg` and keep it.** It is at `/mnt/UDISK/printer_config/printer.cfg` on the Pad.
   3. Copy the contents of `printer/config/printer.cfg` from this repo into the editor. Save.
   4. If the Pad rewrites or hides `printer.cfg` when you pick a printer model, note that in `docs/build/test-log.md`. The Pad's "custom printer" flow is unverified. See research R3.
   📷 The Fluidd editor with the new config saved.
6. Find the MCU serial id. Fluidd does not list USB devices. Plug the SKR into the **desktop** with USB and run `ls /dev/serial/by-id/`. The name is the same on the Pad. Look for `usb-Klipper_lpc1769_...`.
   Put the full name in `[mcu] serial:` in `printer/config/printer.cfg` (task T035). Save the file on the Pad too, then plug the USB back into the Pad and run `FIRMWARE_RESTART` in the console.
   If you prefer, use SSH on the Pad (decision 3 allows it when needed) and run `ls /dev/serial/by-id/` there.
   📷 The `ls` output, showing the full serial id.
7. Check the link and the driver. In the Fluidd console run each line and note the result:

   ```text
   STATUS
   DUMP_TMC STEPPER=stepper_x
   FORCE_MOVE STEPPER=stepper_x DISTANCE=10 VELOCITY=5
   FORCE_MOVE STEPPER=stepper_x DISTANCE=-10 VELOCITY=5
   ```

   The motor must turn one way, then the other. If Klipper says it cannot connect or shows a version or protocol mismatch, read `klippy.log` and use the fallback in `printer/firmware/README.md` step 4.
   📷 The console showing `Klipper state: Ready` and the `DUMP_TMC` output.
8. Check the other four sockets. With the PSU unplugged, move the driver and the motor to each socket in turn: `YM`, `ZAM`, `E0M` and `E1M`. For each one:
   1. Set the socket's UART jumpers the same as for `XM`.
   2. Edit `[stepper_x]` and `[tmc2209 stepper_x]` to that socket's pins in the table below.
   3. Run `FIRMWARE_RESTART`, then `DUMP_TMC STEPPER=stepper_x` and the two `FORCE_MOVE` lines.

   When done, put the `XM` pins back.

   | Socket | `step_pin` | `dir_pin` | `enable_pin` | `uart_pin` |
   | :-- | :-- | :-- | :-- | :-- |
   | `XM` | `P2.2` | `P2.6` | `!P2.1` | `P1.10` |
   | `YM` | `P0.19` | `P0.20` | `!P2.8` | `P1.9` |
   | `ZAM` | `P0.22` | `!P2.11` | `!P0.21` | `P1.8` |
   | `E0M` | `P2.13` | `!P0.11` | `!P2.12` | `P1.4` |
   | `E1M` | `P1.15` | `P1.14` | `!P1.16` | `P1.1` |

   📷 One photo per socket with the driver in place, and one of each `DUMP_TMC` output.
9. Fit the other drivers. With all power off, fit drivers in the other four sockets.
   Check that `DUMP_TMC STEPPER=stepper_x` still reads, with the config on the `XM` pins.
   📷 The board with all five drivers fitted.

## Pre-power checklist

Do not power on until every box is ticked.

- [ ] The PSU is unplugged and USB is removed.
- [ ] Polarity checked on `POWER` (V+ and V-), as in `docs/wiring/00-power-and-host.md`.
- [ ] No loose strands or bare wire near other terminals.
- [ ] Each fitted driver matches the socket silkscreen. `DIAG` pin removed.
- [ ] The motor is connected to the socket you are testing, and nothing else is connected.
- [ ] A second look at the photos above.

## Exit test

The phase passes only if every check passes.

1. Fluidd shows the MCU connected and Klipper `Ready`, with no protocol or version error. Expected: the Pad's Klipper accepts the mainline SKR. PASS / FAIL.
2. `DUMP_TMC STEPPER=stepper_x` returns register values (no "Unable to read tmc uart" error) on the `XM` socket. PASS / FAIL.
3. `FORCE_MOVE STEPPER=stepper_x DISTANCE=10 VELOCITY=5` turns the motor, and `DISTANCE=-10` turns it back. PASS / FAIL.
4. Steps 7 and 8 pass on all five sockets: `XM`, `YM`, `ZAM`, `E0M` and `E1M`. PASS / FAIL.
5. The MCU serial id is written in `printer/config/printer.cfg`. PASS / FAIL.
6. `printer.cfg` on the Pad matches `printer/config/printer.cfg` in the repo (the `XM` pins). PASS / FAIL.

## Record

Add this row to `docs/build/test-log.md` when the exit test is done.
Put the serial id and any protocol note in Notes:

| Date | Phase/Task | Test | Result | Constitution | Notes |
| :-- | :-- | :-- | :-- | :-- | :-- |
| YYYY-MM-DD | Phase 02 / T035 | Pad sees mainline SKR over USB, 5 sockets | PASS or FAIL | II ✔ | serial id, protocol result, per-socket results |
