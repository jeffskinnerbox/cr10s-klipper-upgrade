"""cr10s-status: print what the printer is doing (see contracts/cli.md)."""

import argparse
import json
from dataclasses import asdict, dataclass

from cr10s import cli
from cr10s.moonraker import Moonraker


@dataclass(frozen=True)
class PrinterState:
    """One poll snapshot (data-model.md, PrinterState)."""

    reachable: bool
    klippy_state: str | None = None
    print_state: str | None = None
    filename: str | None = None
    progress: float | None = None
    extruder_temp: float | None = None
    bed_temp: float | None = None
    message: str | None = None


def poll(mr: Moonraker) -> PrinterState:
    """Read one snapshot. Objects the host does not report come back as None."""
    status = mr.query_objects()
    webhooks = status.get("webhooks", {})
    stats = status.get("print_stats", {})
    return PrinterState(
        reachable=True,
        klippy_state=webhooks.get("state"),
        print_state=stats.get("state"),
        filename=stats.get("filename"),
        progress=status.get("virtual_sdcard", {}).get("progress"),
        extruder_temp=status.get("extruder", {}).get("temperature"),
        bed_temp=status.get("heater_bed", {}).get("temperature"),
        message=stats.get("message") or webhooks.get("state_message"),
    )


def _temp(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f} C"


def render(state: PrinterState) -> str:
    progress = "-" if state.progress is None else f"{round(state.progress * 100)}%"
    lines = [
        f"Klipper:  {state.klippy_state or '-'}",
        f"Print:    {state.print_state or '-'}",
        f"File:     {state.filename or '-'}",
        f"Progress: {progress}",
        f"Extruder: {_temp(state.extruder_temp)}",
        f"Bed:      {_temp(state.bed_temp)}",
    ]
    if state.message:
        lines.append(f"Message:  {state.message}")
    return "\n".join(lines)


def _body(ctx: cli.Context) -> None:
    try:
        with Moonraker.from_context(ctx) as mr:
            state = poll(mr)
    except cli.Unreachable:
        if ctx.args.json:
            print(json.dumps(asdict(PrinterState(reachable=False))))
        raise
    print(json.dumps(asdict(state)) if ctx.args.json else render(state))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cr10s-status", description=__doc__, parents=[cli.common_parser()]
    )
    return cli.run("status", parser, _body, argv)
