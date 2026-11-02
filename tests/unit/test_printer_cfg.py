"""Printer config sections must be standard Klipper ones (Constitution III, portable config)."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CFG_FILES = sorted((ROOT / "printer" / "config").glob("*.cfg"))
ALLOWED_FILE = ROOT / "tests" / "fixtures" / "klipper_sections.txt"
HEADER = re.compile(r"^\[([^\]]+)\]")
SAVE_CONFIG = "#*# <---------------------- SAVE_CONFIG"
NUMBERED = re.compile(r"^(extruder|stepper_[xyz])\d+$")

pytestmark = pytest.mark.unit


def allowed_types() -> set[str]:
    lines = ALLOWED_FILE.read_text().splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def section_types(text: str) -> list[str]:
    """First word of every ``[header]``, skipping the SAVE_CONFIG block."""
    found = []
    for line in text.splitlines():
        if line.startswith(SAVE_CONFIG):
            break
        match = HEADER.match(line)
        if match:
            found.append(match.group(1).split()[0])
    return found


def unknown(types: list[str], allowed: set[str]) -> list[str]:
    return [
        t
        for t in types
        if t not in allowed and NUMBERED.sub(lambda m: m.group(1), t) not in allowed
    ]


def test_allowlist_has_the_core_sections():
    allowed = allowed_types()
    for name in (
        "mcu",
        "printer",
        "stepper_x",
        "tmc2209",
        "extruder",
        "heater_bed",
        "bltouch",
        "gcode_macro",
        "include",
        "display_status",
        "virtual_sdcard",
    ):
        assert name in allowed


def test_section_types_reads_first_word_and_stops_at_save_config():
    text = (
        "[mcu]\nserial: x\n[tmc2209 stepper_x]\n[gcode_macro START]\n"
        + SAVE_CONFIG
        + " ----------------------\n[bed_mesh default]\n"
    )
    assert section_types(text) == ["mcu", "tmc2209", "gcode_macro"]


def test_unknown_sections_are_reported_and_numbered_ones_accepted():
    allowed = allowed_types()
    assert unknown(["mcu", "stepper_z1", "extruder1", "creality_magic"], allowed) == [
        "creality_magic"
    ]


@pytest.mark.parametrize("cfg", CFG_FILES or [None], ids=lambda p: p.name if p else "no-cfg")
def test_cfg_files_use_only_standard_sections(cfg):
    if cfg is None:
        pytest.skip("no printer/config/*.cfg yet")
    bad = unknown(section_types(cfg.read_text()), allowed_types())
    assert not bad, f"non-standard sections in {cfg.name}: {bad}"
