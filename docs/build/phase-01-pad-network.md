# Phase 01: Sonic Pad on the network

## Purpose

Put the Sonic Pad on your LAN with a fixed address and a name, let the desktop talk to its Moonraker API, and record which ports it uses. After this phase `cr10s-status` and the live test can reach the Pad.

The printer is not touched: no SKR board, no wiring, nothing connected to the CR-10S. This is user story US1, plan Phase 1 (task T025).

## Parts and tools

- Parts:
  - 1 Sonic Pad with the power supply it shipped with
  - 1 Ethernet cable, Pad to your router or switch
- Tools:
  - Desktop with a browser and a terminal
  - Access to your router's admin page (DHCP reservations)

## Risky steps and recovery

| Step | Risk | Undo or recover |
| :-- | :-- | :-- |
| 3 | A reservation that clashes with another device breaks both. | Pick an address outside the router's DHCP pool, or delete the reservation and let the Pad take a new lease. |
| 5 | A wrong edit to `moonraker.conf` can stop Moonraker from starting, and you lose the UI. | Copy the whole file into a local text file first. Fluidd also keeps a `.bkp` copy. Paste the original back and restart. |
| 5 | `trusted_clients` set too wide (a whole subnet, or `0.0.0.0/0`) lets any device on the LAN control the printer without a key. | Use the desktop's single address (`/32`), never a wide range. |

## Steps

Write every address and port you find into `docs/build/test-log.md` (Notes column) as you go.

1. Plug the Ethernet cable into the Pad and the router. Power the Pad on and wait until the touchscreen shows the home screen.
   📷 The Pad home screen, with the Ethernet cable visible in the port.
2. Find the Pad's IP address. Look at the network or Wi-Fi settings page on the touchscreen (menu names differ between firmware versions). If you cannot find it there, look for the Pad in your router's list of connected devices. Write the address down as `PAD_IP`.
   📷 The screen or router page that shows `PAD_IP` and the Pad's MAC address.
3. In the router, add a DHCP reservation so `PAD_IP` always goes to the Pad's MAC address. If the router lets you give the device a name, name it `sonicpad` so `sonicpad.lan` resolves. If it does not, add this line to `/etc/hosts` on the desktop instead (replace the address):

   ```bash
   echo "PAD_IP sonicpad.lan" | sudo tee -a /etc/hosts
   ```

   📷 The router's reservation page showing the MAC address, `PAD_IP` and the name.
4. Find the ports. The web UI should answer on port 80, and Moonraker on 7125 or 7128 (or through the UI port). Try each and note which return JSON:

   ```bash
   curl -s -m 5 http://sonicpad.lan/server/info
   curl -s -m 5 http://sonicpad.lan:7125/server/info
   curl -s -m 5 http://sonicpad.lan:7128/server/info
   ```

   Open `http://sonicpad.lan` in a browser and check that Fluidd loads. If every curl fails with a "forbidden" or empty answer, that is normal until step 5. Look at the error text and move on.
   📷 The terminal with the three curl results, and the Fluidd page in the browser.
5. Let the desktop in. Find the desktop's address as the Pad sees it:

   ```bash
   ip -4 route get PAD_IP
   ```

   Read the address after `src`. Call it `DESKTOP_IP`. In Fluidd, open the configuration (config files) page, open `moonraker.conf`, and copy its full text to a local file first. Add or extend this section, using the single address with `/32`:

   ```ini
   [authorization]
   trusted_clients:
       DESKTOP_IP/32
   ```

   Save and restart Moonraker (Fluidd's "save and restart" button, or restart the service from the Fluidd menu). If Fluidd will not let you edit `moonraker.conf`, stop here and write down what it shows. Do not try other ways in yet.
   📷 The `[authorization]` section in the editor, after saving.
6. Repeat the curl for the port that worked in step 4. Now it must return JSON with a `klippy_state` key. The value can be anything (`ready`, `error`, `disconnected`): the printer is not connected yet.
   📷 The terminal with the JSON answer.
7. Record what the status query returns while Klipper is not ready. This tells us how the tools must behave in this state:

   ```bash
   curl -s -m 5 -i "http://sonicpad.lan:PORT/printer/objects/query?webhooks&print_stats"
   ```

   Write down the HTTP status line (200 or 503) and the body. Leave off `:PORT` if Moonraker is reached through the UI port.
8. Set the address in the tool config. Make `~/.config/cr10s/config.toml` from `config.example.toml` if you have not already, and set `pad.url` to the working address, adding `:PORT` only if Moonraker needs it:

   ```toml
   [pad]
   url = "http://sonicpad.lan:7125"
   ```

## Pre-power checklist

Tick every box before step 1.

- [ ] The Pad uses its own power supply, not a different adapter.
- [ ] The Ethernet cable is seated at both ends.
- [ ] Nothing else is connected to the Pad (no printer, no SKR board).

## Exit test

Every check must pass.

1. `ping -c 3 sonicpad.lan` gets three replies. PASS / FAIL.
2. Reboot the Pad. When it is back, `ping -c 3 sonicpad.lan` still answers at the same address. PASS / FAIL.
3. `http://sonicpad.lan` loads Fluidd in the browser. PASS / FAIL.
4. `curl -s -m 5 <pad.url>/server/info` returns JSON with a `klippy_state` key. PASS / FAIL.
5. `uv run cr10s-status` finishes within 15 seconds and prints something (exit 0, or exit 3 with an HTTP status in the message when Klipper is not ready). It must not hang. PASS / FAIL.
6. The ports (UI, Moonraker) and the answer from step 7 are written down. PASS / FAIL.

## Record

Add this row to `docs/build/test-log.md` when the exit test is done, with the ports and the step 7 answer in Notes. Then record the ports in `docs/decisions.md` under Assumptions (task T025):

| Date | Phase/Task | Test | Result | Constitution | Notes |
| :-- | :-- | :-- | :-- | :-- | :-- |
| YYYY-MM-DD | Phase 01 / T025 | Pad on the network exit test | PASS or FAIL | II ✔ VI ✔ | UI port, Moonraker port, step 7 answer |
