# My 3D Print Upgrade

In December of 2018, I purchased the [Creality CR-10S][01] (aka CR-10S 300)
with a build area of 300x300x400mm from Gearbest for $420, including shipping.
It has served me well, but it has become increasingly clear that some basic upgrades could improve its performance.
When the excitement about [Klipper][02] reached me (2025), I felt it was time to act.
I began by building a vision of what an upgrade might look like.

Klipper doesn't work alone.
[Klipper][02] is the brain, [Moonraker][27] is the API, and [Fluidd][28] / [Mainsail][29] are interchangeable dashboards.

- Klipper replaces [Marlin’s][09] role of commanding all 3D printer operations.
- Moonraker is a Python web server and API in front of Klipper.
- Fluidd / Mainsail are web UIs, accessed from any browser on your network.

---

## Upgrade Vision

**Goal: Speed + Quality + Quiet Operation**

To reach this goal,
these are the Creality CR-10S upgrade recommendations harvested from Internet websites.
Upgrades are listed in priority order, with a suggested installation sequence at the bottom.

1. Improved Print Control + UI - **[Creality Sonic Pad + Klipper][13]**<br>
   Klipper can provide faster and cleaner prints.
   The existing Marlin is a good appliance,
   but Klipper + Moonraker + Mainsail is more like a tunable platform
   and with the Sonic Pad you get a more capable user experience.
1. Stepper Drivers - **[Bigtreetech (BTT) TMC2208 or TMC2209 with drop-in stepper drivers][12]**<br>
   The CR-10S stock drivers are loud.
   TMC2208/2209s are the single biggest bang-for-buck upgrade —
   near-silent motion. Klipper has excellent TMC support
   (UART mode, stealthChop, spreadCycle tuning).
   The 2209s are preferred as they also support sensorless homing.
1. Bed Leveling - **[CR Touch Auto Leveling Sensor][14]**<br>
   Klipper's `bed_mesh` feature is excellent, but requires a probe. On a 300x300 bed this matters a lot;
   manual leveling a large bed is tedious and the CR-10S bed is known to warp. The CR Touch is
   cheaper and works fine with Klipper.
1. Extruder - **[BMG (Bondtech Mini Geared) Extruder][15]**<br>
   The stock CR-10S extruder is a single-drive arm-style unit that skips under pressure. A dual-drive
   extruder dramatically improves filament grip, which matters even more at the higher speeds you'll
   get with Klipper.
1. Hot End - **[Micro Swiss All-Metal Hot End][11]**<br>
   The stock PTFE-lined hot end limits you to ~240°C max safely. An all-metal hot end opens up ABS,
   ASA, and PETG at higher speeds, and pairs well with Klipper's pressure advance tuning.
1. Part Cooling - **[WINSINN 50mm 5015 Blower Fan 12V 7500RPM][16]**<br>
   Klipper's higher speeds expose weak part cooling quickly. The stock fan is mediocre. A 5015 blower
   significantly improves overhangs and bridging at speed.
   See Printables and other 3D model sites for 5015 Blower Fan Retrofit Adapter.
   My CR-10S has a 12 volt power supply.
1. Input Shaper (Resonance Compensation) - **[ADXL345 accelerometer][10]** (in Sonic Pad Kit)<br>
   The Sonic Pad includes one — confirm your kit has it. Klipper's input shaper (`resonance_tester`)
   measures your printer's actual resonance frequencies and compensates automatically. This is what
   lets you push speed without ringing artifacts, and is essential for getting the most out of the
   Sonic Pad.
1. Frame Rigidity - **[Dual Z-axis Lead Screw Kit][17]** (already installed)<br>
   The original CR-10S was a single-Z stock, which causes Z-wobble and layer inconsistency at speed.
   To correct this, Creality sells an official dual-Z kit, but my CR-10S has dual Z-axis screws.
   Klipper also supports `Z_TILT_ADJUST` to automatically level dual-Z setups.
1. Nice-to-Have Additions

   |           Upgrade            |                                        Benefit                                        |
   | :--------------------------: | :-----------------------------------------------------------------------------------: |
   | [PEI spring steel sheet][18] |           Replaces glass bed; far better adhesion, prints pop off when cool           |
   | [Capricorn PTFE tubing][19]  |      Tighter 1.9mm ID (vs 2.0mm stock) reduces Bowden play, improves retraction       |
   |          USB webcam          | Remote monitoring beyond what the Sonic Pad offers (Pad handles most of this already) |

1. Suggested Order of Implementation
   1. **TMC drivers + Sonic Pad/Klipper** — do these together as one job
   1. **CR Touch** — configure `bed_mesh` in Klipper immediately after
   1. **Dual-Z Kit** — make sure to enable `Z_TILT_ADJUST` in Klipper config
   1. **BMG dual-drive extruder** — tune pressure advance in Klipper after install
   1. **PEI sheet** — easy win, do whenever
   1. **All-metal hot end + 5015 fan** — prioritize if printing anything beyond PLA

---

## Upgrade Plan

In this section, I identify all the items I have purchased for the upgrade I'm doing at this time.
This does not cover all the items in the Upgrade Vision,
but to me it does address the most important ones.

### 3D Printer Controller Hardware: Creality Sonic Pad

The [Creality Sonic Pad][13] is a Klipper-based touchscreen tablet designed to supercharge
your FDM (Fused Deposition Modeling) 3D printer.
It significantly boosts printing speeds and quality through advanced resonance compensation (input shaping).

The Sonic Pad comes pre-configured for most popular Creality models,
like the Ender-3 V3, Ender-3 S1, and CR-10 series.
Setup takes about 10–20 minutes, involving selecting your printer model,
updating the firmware via USB, and calibrating the device.
While it is intended for Creality printers,
the community has also adapted it for various third-party machines.

Key Features:

- **Lightning-Fast Speeds:** Powered by a 64-bit SoC,
  it replaces your printer's standard firmware (like [Marlin][09])
  to allow drastically increased print speeds without sacrificing model quality.
- **Input Shaping:** Uses an included accelerometer to measure and cancel out
  printer vibrations, mitigating ghosting and ringing at high speeds.
- **Remote Management & Monitoring:** Features built-in WiFi and Ethernet.
  By plugging in a USB webcam, you can monitor prints remotely and record time-lapses.
- **Multi-Printer Control:** Capable of running and controlling up to four different FDM printers simultaneously via USB.

> **Advanced Resonance Compensation (Input Shaping)**
> is a firmware-level technique that cancels out machine vibrations by modifying motion commands.
> It eliminates ringing, ghosting, and rippling on printed surfaces,
> allowing you to push 3D printers to much higher speeds and accelerations without sacrificing quality.
>
> **The Problem:** When a printhead or bed rapidly changes direction, the mechanical parts (frames, belts) flex and vibrate.
> These vibrations show up as wavy patterns (ringing) on your prints.
>
> **The Solution:** Input shaping artificially creates an opposing vibrational wave in the control signal.
> When the opposing wave meets the physical vibration, they cancel each other out.

### 3D Printer Controller Software: Klipper

Klipper is open-source firmware for 3D printers.
It splits the work between two computers:

1. A host, usually a Raspberry Pi or similar Linux single-board computer (SBC), runs Python.
   It does the heavy math: parsing G-code, motion planning, and kinematics.
1. The printer's mainboard microcontroller (MCU) just executes precisely timed step commands from the host.

Traditional firmware like [Marlin][09] is the opposite: everything runs on the small MCU, in C++.

Why people use it:

- **Speed and quality.**
  Features like input shaping cancel frame vibrations (ringing), and pressure advance improves corners.
- **No re-flashing for changes.**
  Configuration lives in a text file, `printer.cfg`.
  You edit it and restart, with no recompiling.
  That's also where you'd define the Bigtreetech SFS V2.0 (Smart Filament Sensor)'s pins.
- **Web UI.**
  It's usually paired with [Mainsail][04] or [Fluidd][05] (via the [Moonraker API][06]) to control the printer from a browser.
- **Macros**
  in [G-code][08] with [Jinja2 templating][07], and Python if you want to write extensions.

The trade-off is that you need the extra host computer and some Linux comfort, which shouldn't be a hurdle for me.

### 3D Printer Slicer: OrcaSlicer

When it comes to slicing, what I currently use, [UltiMaker Cura][23],
is inferior to [OrcaSlicer][41] and [PrusaSlicer][42],
which have better Klipper integration, including direct upload to Moonraker.

I choose to use OrcaSlicer because it has a richer set of Klipper features
and tighter integration with Moonraker.
OrcaSlicer should be hosted on my desktop Ubuntu system and on the same network as the Sonic Pad.

### 3D Printer Integration: Moonraker

Moonraker is a Python web server and API in front of Klipper.
It handles:

- File uploads and print job management.
- Webcam streams.
- Notifications.
- Update management.
- Power control.
- Integration with Home Assistant, OctoEverywhere, and similar services.

Fluidd / Mainsail UIs are useless without Moonraker.
Moonraker handles file management and updates, and the UIs just present them.
Moonraker has to run on the same host as Klipper.

### 3D Printer User Interface: Mainsail

Fluidd and Mainsail have a nearly 100% overlap.
Both are front ends to Moonraker with the same core features and differ mostly in layout and polish.
You can pick one, and you can switch later without losing anything.
They provide:

- Temperature graphs.
- A G-code console.
- Macros.
- A config editor.
- Job queue and history.
- Webcam view.

I prefer Mainsail over Fluidd because of its larger community and more tutorials/guides online.
I may try Fluidd later.
Mainsail (and Fluidd) are static web apps.
The browser loads them and talks to Moonraker over HTTP and WebSocket.
They can be served from any machine on your network, or from a Docker container in my homelab.
I want my Mainsail to be hosted on the Sonic Pad with Klipper.

### 3D Printer Driver: Bigtreetech SKR V1.4

The [Bigtreetech](https://biqu.equipment/collections/control-board)
(BTT) SKR V1.4 is the "brain" and central motherboard of your 3D printer.
It processes G-code from your computer or SD card, tells the motors exactly how to move,
and regulates temperatures for the hot end and heated bed.

Upgrading to the SKR V1.4 provides several notable enhancements:

- **32-Bit Processing:** Unlike older 8-bit boards, the 32-bit architecture processes commands much faster.
  This allows for smoother curves, faster print speeds, and easier firmware updates via SD card.
- **Silent Stepper Motor Drivers:** The board has sockets for upgraded, removable motor drivers (like the popular TMC2209s),
  which eliminate the loud, whining motor noises and add features like "sensorless homing"
  (finding zero without needing physical end stop switches).
- **Extensive Upgradability:** It features built-in expansion ports for modern upgrades like a CR Touch for auto bed leveling,
  filament run-out sensors, RGB light strips, and even a WiFi module.
- **Dual Z-Axis Support:** It includes dedicated, independent ports for running two separate stepper motors on your Z-axis,
  making leveling much easier.

> In the Bigtreetech (BTT) SKR series of 3D printer motherboards,
> "SKR" is widely believed to be an abbreviation based on the Chinese Pinyin for Shuai Ke Ran,
> which translates loosely to "Cool, Agile, and Decisive" or "Speedy."
> While Bigtreetech has never explicitly published an official, literal acronym for it in English,
> the SKR line is highly recognizable as their baseline of open-source,
> 32-bit control boards designed for makers and DIY upgraders.

### 3D Printer Sensor: Smart Filament Sensor

[BTT SFS (Bigtreetech Smart Filament Sensor) V2.1 Break Detection Module][03]
is a filament watchdog for your 3D printer.
Filament passes through it on the way to the extruder, and it watches for two problems:

1. **Run-out**, the filament ending or breaking. A simple switch detects whether filament is present, like a door sensor.
1. **Jams, clogs, and tangles**. An optical encoder wheel turns as filament moves.
   If the printer is extruding but the wheel stops, something is stuck.
   It's like the wheel-speed sensors in a car's ABS:
   the engine says "go," the wheel says "not moving," so something's wrong.
   BTT rates the detection length at 2.88mm, meaning it notices quickly when movement stops.

When either problem happens, the firmware pauses the print so you don't waste filament.
You fix the problem and resume.
The sensor's LED turns solid red when filament is used up or broken, and it reads movement in both directions,
so mounting orientation doesn't matter.
It only works with 1.75mm filament.

The sensor has two signals. A switch output detects run-out, like a door sensor.
An encoder output detects whether filament is moving, which catches clogs and tangles, like a wheel-speed sensor.
Each signal goes to an I/O pin on the board, and then you configure your firmware.

### 3D Printer Sensor: Touch Auto Bed Leveling

The [Creality CR Touch Auto Bed Leveling Sensor Kit][14]
is Creality's auto bed-leveling probe, essentially their version of the BLTouch.

How it works: An electromagnet drops a small metal pin.
When the pin touches the bed, an optical sensor detects the contact and the firmware records the height.
It probes a grid of points, builds a height map of the bed,
and compensates for tilt and warp during printing.
Creality rates the accuracy at about 0.04mm; it runs on 5V,
and the metal pin lasts longer than older plastic pins.

For my current CR-10S (pre-upgrade), this sensor will not work.
Creality's plug-and-play firmware targets 32-bit boards like their 4.2.2 and 4.2.7.
My stock CR-10S board is an older 8-bit board, so it's not a simple drop-in on stock electronics.

With the SKR V1.4, it works well:

- It uses the same firmware support as the BLTouch, so you configure it as a BLTouch.
- Marlin: connect it to the board's servo/probe port and enable the BLTouch settings.
- Klipper: a `[bltouch]` section plus `[bed_mesh]` in `printer.cfg`.
- You'll need a mount for your hot end and an adapter cable (CR Touch connectors often don't match SKR pinouts),
  and you'll typically remove or bypass the **Z endstop switch** so the probe does Z homing.

### Upgrade Guides / Sources

A quick search of the Internet found nothing that covers exactly my combination of features
(CR-10S with an SKR 1.4 board, run from a Sonic Pad).
You find below a grouping of web posts and videos that cover parts of my build.

- Most recent and closest match
  - [BTT SKR v1.4 / v1.4 Turbo + TMC2209 complete guide (3dwork.io)][30]
    is about 6 months old.
    It covers TMC2209 drivers, sensorless homing, and compiling Klipper for the SKR 1.4,
    and points to a Klipper `printer.cfg` starting point.
    It also links to companion guides on first steps, calibration, and troubleshooting.

- Same printer, near-identical board (CR-10S + SKR + TMC2209 + Klipper)
  - [marcogabriel/klipper-config-skr-1.3-creality-cr-10s (GitHub)][31]
    is a CR-10S config (undated).
    It uses the second extruder driver for the second Z motor. That’s relevant to your dual-Z setup.
    The SKR 1.3 and 1.4 are very close, so adapting the pins should be a small job.
  - [simeonpashley/klipper_config (GitHub)][32]
    is an Ender 3 V2 with SKR 2, CR Touch, dual-Z and TMC2209.
    The author warns that CR Touch wiring differs a lot from BLTouch and says they fried one with wrong wiring.
    That’s worth reading before you wire yours to the SKR 1.4.
  - [sajrashid/klipper_config (GitHub)][33]
    uses an SKR 1.4 with a BLTouch-type probe, Moonraker and Fluidd.
    It has probe offset and mesh calibration steps.

- SKR 1.4 / TMC2209 videos (older, but still the standard references)
  - [SKR 1.4 – TMC2209 v1.2 UART (Chris’s Basement)][34]
  - [SKR 1.4 – TMC2209 with sensorless homing (Chris’s Basement)][35]
  - Both are from the SKR 1.4 playlist you already cite.
    I’d treat them as hardware-wiring references only,
    since they’re several years old.

- BTT SFS V2 with Klipper
  - [Voron docs: Setup a BTT Smart Filament Sensor][38]
    is the best written guide I found.
    It warns that sensorless homing/StallGuard can interfere with the sensor if the DIAG pin is set on the MCU where the sensor is connected,
    and it recommends disabling the sensor at Klipper start.
    That matters because you want both sensorless homing and the SFS.
  - [BTT SFS V2 2020 Mount (Printables)][39]
    has a working Klipper config with separate switch and encoder sensors and enable/disable macros.

- Sonic Pad
  - [Creality Sonic Pad support article (Dremc)][40]
    covers setup, input shaping, pressure advance, and reverting to stock firmware, with video timestamps.
  - This is where your plan hits a snag. The Sonic Pad store page lists the product as discontinued.
    Its official support covers only listed printers and mainboards,
    and for custom boards you build Klipper firmware yourself using Creality’s custom-printer install manual.
    The CR-10S with an SKR board falls in that custom category. I found no recent walkthrough of that exact path.

- Gaps
  - I found no recent guide pairing CR Touch with an SKR 1.4 under Klipper, only the BLTouch-style configs above.
  - I found no recent guide for the BMG, Micro Swiss, or 5015 fan on a CR-10S.
  - I found no confirmed publication dates on most of the above, so "recent" is a best guess.

- Other Potential Sources
  - [Sonic Pad Basics](https://www.youtube.com/playlist?list=PLC4bOo0vesmLWWEeBWwv6oR4QzhP-0ctf)
  - [Creality Sonic Pad in-depth review | Faster, easier 3D printing?](https://www.youtube.com/watch?v=IybJlj0WqKg)
  - [Klipper On 4 3d Printers? Creality Sonic Pad 3 Months Later](https://www.youtube.com/watch?v=5Sz-cGuHZn4)
  - [Maximizing Acceleration with the Sonic Pad on the CR-10S Pro V2 - Print speed is only half the story](https://www.youtube.com/watch?v=_socSGTgGcw)
  - [The 10 Upgrades I Install on EVERY Klipper 3D Printer](https://www.youtube.com/watch?v=h6g8DoTc7ys)
  - [Klipper Setup](https://www.youtube.com/playlist?list=PLC4bOo0vesmLJ211bmSiWaJ9ahBUQUjjv)
  - [Input Shaper - Klipper - Chris's Basement - 2023](https://www.youtube.com/playlist?list=PLB_0YGFjbOnZroPzoxA12NfsGMBCxctwH)
  - [BigTreeTech SKR v1.4 First Look! | Overview & New Features](https://www.youtube.com/watch?v=pACQwIcyTtI&t=6s)
  - [Bigtreetech SKR V1.4 (Turbo) comprehensive guide](https://www.youtube.com/watch?v=-Gdk0wHg51w)
  - [SKR V1.3 32bit control board upgrade for CR-10](https://www.youtube.com/watch?v=B7gzDwh8UEM)
  - [SKR 1.4 Tutorials](https://www.youtube.com/playlist?list=PLP-VDZmS6bFo6qyPS8MyBFKqepQHpjCEB)
  - [BIGTREETECH Wiki for SKR V1.4](https://global.bttwiki.com/SKR%20V1.4.html)
  - [BigTreeTech SKR v1.4 Mainboard - Full Install Part 1 - 2209 Drivers - Chris's Basement](https://www.youtube.com/watch?v=oHMZ0ocTYvM)
  - [SKR V1.3 32-bit board upgrade for the CR-10](https://3dpblog.com/skr-32bit-control-board-upgrade-cr10/)
  - [How to set up the Bigtreetech SFS v2 on Klipper](https://www.youtube.com/watch?v=FNqQoJazBSE)

### One Concern

Well after the time I purchased the Sonic Pad,
I discovered there is some evidence that Creality may have discontinued it as a product.
The risk appears to be manageable.

Why it’s manageable:

- **The Creality Sonic Pad is swappable.**
  The Sonic Pad is only the host.
  Your SKR 1.4 runs Klipper firmware built from mainline sources, and your `printer.cfg` is plain text.
  If the Pad fails or you outgrow it, you can move the config to a Pi or BTT Pad 7 without touching the printer’s wiring.
  Treat it as a replaceable server, like a VM you can migrate.
- **Hardware support isn’t the issue.**
  It’s a normal Linux board. The weak spot is Creality’s modified Klipper software, which mainline maintainers won’t support.
- **The community has workarounds.**
  The Debian-on-Sonic-Pad route exists for running mainline Klipper on the hardware, but I haven’t verified it still works.

Where it’s riskier:

- The CR-10S with an SKR 1.4 is a custom printer for the Sonic Pad,
  so Creality’s official support doesn’t cover it.
  Expect to rely on community help.
- Creality’s fork may lag behind mainline Klipper features and fixes,
  and it won’t get new ones if the product is end of life.
- Users report problems like MCU disconnects, and Creality’s support has drawn criticism,
  including on a CR-10S.

What you should do:

- Keep your config portable.
  Avoid Creality-specific macros and keep everything in standard Klipper sections.
- Version your `printer.cfg` in git, as in [new-workflow.md](new-workflow.md).
- Keep a [BIGTREETECH Pad 7][43] in mind as your fallback.
  It costs little, and you wouldn’t need to rewire anything.

---

## Current 3D Printing Environment & Workflow

This is an accurate description of how I work today with my 3D printer.

### Environment

My 3D print platform is the [Creality CR-10S][01] (aka CR-10S 300) with a build area of 300x300x400mm.
The CR-10S hardware and software have not been modified in any substantial way other than
eliminating the control box and moving all the electronics under the printer (much like this [video][26]).

The 3D printer is physically in my home, and co-located with my homelab.
When needed, the desktop computer provides me additional computing (e.g., CAD tool, slicer).

### Workflow

Today, my 3D print projects start with a CAD tool like [FreeCAD][20] or [OpenSCAD][21],
running on my desktop Ubuntu computer,
where a physical design is created and an [STL file][22] is generated.
I then manually move the STL file into the [UltiMaker Cura][23] [3D slicer engine][24]
(also on the desktop Ubuntu computer)
to create the required [G-code][25] for the Creality CR-10S.
I then download the G-code onto an SD card and physically insert it into the Creality CR-10S.
I then start the CR-10S to render the object.

---

## Future 3D Printing Environment & Workflow

This is how I would like to work with my 3D printer in the future.

### Environment

The 3D printer is physically in my home, and co-located with my homelab,
where I plan to network the Creality Sonic Pad to my Ubuntu desktop computer.
When needed, the desktop computer provides me additional computing (e.g., CAD tool, slicer)
and networking (e.g., Internet, SSH) to support the Sonic Pad and its control of the CR-10S.

### Workflow

My objective is that the workflow should not be as manual and ad hoc as the current workflow.
Details, scripts, and sources are in [new-workflow.md](new-workflow.md).
In brief:

- **Split of duties.**
  The desktop designs, slices, and automates.
  The Sonic Pad stores the G-code, runs the print, and serves the web UI.
- **One command.**
  Each project is a git repo with a `Makefile`.
  `make upload` exports the STL (OpenSCAD or FreeCAD), slices it with the OrcaSlicer command line, and uploads the G-code to Moonraker.
- **Manual start.**
  I clear the bed and start the print myself from Mainsail or the touchscreen.
- **Monitoring.**
  A small watcher script polls Moonraker and sends notifications.
  `moonraker-telegram-bot` is an option for webcam pictures and remote pause.
- **Open items.**
  The Pad's Moonraker is old and modified, so notifier support, the Moonraker port, and Mainsail availability need to be verified.

[01]: https://www.creality3dofficial.com/products/official-creality-cr-10s-3d-printer
[02]: https://www.klipper3d.org/
[03]: https://github.com/bigtreetech/smart-filament-detection-module/blob/master/V2.0/Manual/SFS%20V2.0%20User%20Manual_20231123.pdf
[04]: https://docs.mainsail.xyz/
[05]: https://docs.fluidd.xyz/
[06]: https://moonraker.readthedocs.io/en/latest/
[07]: https://realpython.com/primer-on-jinja-templating/
[08]: https://marlinfw.org/docs/gcode/
[09]: https://marlinfw.org/
[10]: https://store.creality.com/products/adxl345-vibration-compensation-sensor-for-ender-3-v3-ke
[11]: https://www.matterhackers.com/store/l/micro-swiss-all-metal-hotend-kit-for-creality3d/sk/M3XFTAQN
[12]: https://www.amazon.com/dp/B082QYYFVX
[13]: https://www.creality.com/products/creality-sonic-pad
[14]: https://www.amazon.com/gp/product/B09DVYZSYJ
[15]: https://www.bondtech.se/product/creality-cr-10s-kit/?v=0b3b97fa6688
[16]: https://www.amazon.com/WINSINN-7500PRM-Printer-50mmx15mm-Brushless/dp/B0DJQV6LRL
[17]: https://www.amazon.com/dp/B0GF7L1W2K
[18]: https://www.amazon.com/AJOYIB-Flexible-Adhesive-Magnetic-Compatible/dp/B09T6S6PHJ/
[19]: https://www.amazon.com/Capricorn-Bowden-Filament-Genuine-Premium/dp/B079P92HN9/
[20]: https://www.freecad.org/
[21]: https://openscad.org/
[22]: https://en.wikipedia.org/wiki/STL_(file_format)
[23]: https://ultimaker.com/software/ultimaker-cura/
[24]: https://en.wikipedia.org/wiki/3D_Slicer
[25]: https://en.wikipedia.org/wiki/G-code
[26]: https://www.youtube.com/watch?v=sC4vXBgNvY0
[27]: https://moonraker.readthedocs.io/en/latest/
[28]: https://docs.fluidd.xyz/
[29]: https://docs.mainsail.xyz/
[30]: https://3dwork.io/en/complete-guide-skr-v1-4-and-tmc2209/
[31]: https://github.com/marcogabriel/klipper-config-skr-1.3-creality-cr-10s
[32]: https://github.com/simeonpashley/klipper_config
[33]: https://github.com/sajrashid/klipper_config
[34]: https://www.youtube.com/watch?v=ujaqZknWqTo
[35]: https://www.youtube.com/watch?v=vcEbpjao_1o
[38]: https://docs.vorondesign.com/community/howto/samwiseg0/btt_smart_filament_sensor.html
[39]: https://www.printables.com/model/797870-btt-sfs-v2-2020-mount
[40]: https://support.dremc.com.au/support/solutions/articles/51000321087-creality-sonic-pad
[41]: https://www.orcaslicer.com/
[42]: https://www.prusa3d.com/p/prusaslicer/
[43]: https://biqu.equipment/products/bigtreetech-pad-7
