# SKR V1.4 Klipper firmware

Steps to build the Klipper MCU firmware for the BTT SKR V1.4 (Turbo) and flash it from the SD card. Source: research R2. The built `.bin` is git-ignored. Only `skr14.config` (task T029) is committed.

Work on the bench. Do not connect the board to the printer, the heaters or the PSU yet. The old board stays installed until the bench test passes.

## What you need

- Desktop with `git`, `make`, `gcc-arm-none-eabi`, `libnewlib-arm-none-eabi` and `python3`.
- A microSD card, FAT32, 32 GB or smaller.
- A USB cable from the SKR to the desktop (for the check) and later to the Pad.
- The SKR V1.4 Turbo on the bench. USB power is enough for the flash.

```bash
sudo apt install git build-essential gcc-arm-none-eabi libnewlib-arm-none-eabi python3-dev
```

## 1. Build

```bash
git clone https://github.com/Klipper3d/klipper.git ~/klipper
cd ~/klipper
git rev-parse HEAD        # write this hash in the header of skr14.config
make menuconfig
```

Set these options in `menuconfig`:

| Option | Value |
| :-- | :-- |
| Micro-controller Architecture | LPC176x |
| Processor model | `lpc1769 (120 MHz)` for the Turbo. `lpc1768 (100 MHz)` for the non-Turbo board |
| Bootloader offset | 16KiB bootloader |
| Communication interface | USB |

Save and exit. Then build:

```bash
make clean
make
ls -l out/klipper.bin
```

Copy the options file into this repo, so the build can be repeated (task T029):

```bash
cp ~/klipper/.config printer/firmware/skr14.config   # then re-add the comment header
```

## 2. Flash from the SD card

1. Format the SD card as FAT32. Copy `out/klipper.bin` to the card root and rename it `firmware.bin`.
2. Power the SKR off. Put the card in the SKR slot (not the display slot).
3. Power the SKR on through USB. Wait about 10 seconds.
4. Power it off. Take the card out.
5. Look at the card on the desktop. The bootloader renames the file to `FIRMWARE.CUR` when the flash worked. If it is still `firmware.bin`, the flash did not run.

To flash again, use a **different** file name that is not `FIRMWARE.CUR`, or delete `FIRMWARE.CUR` first. The bootloader ignores a file it has already flashed.

## 3. Check

Plug the SKR into the desktop with USB.

```bash
ls /dev/serial/by-id/
```

You should see `usb-Klipper_lpc1769_...` (or `lpc1768` on a non-Turbo board). Write the full name down. It goes in `[mcu] serial` in `printer.cfg`. If nothing appears, see Troubleshooting.

## 4. Match the Pad's Klipper version

The Pad's Klipper (host) and this firmware (MCU) must speak the same protocol. This is research R2's open check.

1. Connect the SKR to the Pad (USB1) with a minimal `printer.cfg` that has only `[mcu]` and `[printer]`.
2. Restart Klipper from the Pad UI.
3. If the status says `mcu 'mcu': Unable to connect`, or a message such as `Protocol error` or `Version mismatch`, the versions differ. Read `klippy.log` for the two version strings.

### Fallback: build from the Pad's own Klipper tree

Do this only if step 4 shows a mismatch.

1. Find the Pad's Klipper commit. Over SSH (decision 3 allows it when needed), run `cd /usr/share/klipper && git log -1`. If there is no `.git` folder, use the CrealityTech Klipper fork on GitHub that matches the Pad's version string.
2. Clone that tree on the desktop and repeat step 1 (Build) with the same `menuconfig` options.
3. Flash again (step 2). Use a new file name.
4. Record the commit hash in the header of `skr14.config`, and write the result in `docs/build/test-log.md`.

Keep the mainline build for the later move to mainline Klipper.

## Troubleshooting

| Symptom | Likely cause and fix |
| :-- | :-- |
| `firmware.bin` stays on the card | The card is not FAT32, is over 32 GB, or is in the wrong slot. Reformat and retry |
| No `/dev/serial/by-id/usb-Klipper_*` | Flash did not run, or the cable is power-only. Try another cable. Check `dmesg \| tail` |
| Board shows as `Smoothieware` or an LPC bootloader | The firmware was built without USB. Rebuild with Communication interface = USB |
| Flash worked but the Pad cannot connect | Version mismatch. Use the fallback above |
| Board resets in a loop | Wrong bootloader offset. It must be 16KiB. Rebuild and reflash |
