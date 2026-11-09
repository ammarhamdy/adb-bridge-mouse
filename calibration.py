"""Pen digitizer calibration: raw ABS_X/ABS_Y units -> normalized 0..1."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from .adb import adb_command
from .models import PenState


@dataclass(frozen=True, slots=True)
class AxisRange:
    """Inclusive min/max the digitizer reports for one axis."""

    min: int
    max: int

    def normalize(self, value: int) -> float:
        """Map a raw value to 0.0-1.0, clamped (hover can overshoot the edge)."""
        span = self.max - self.min
        if span <= 0:
            return 0.0
        return min(1.0, max(0.0, (value - self.min) / span))


@dataclass(frozen=True, slots=True)
class PenBounds:
    """Digitizer extent on both axes."""

    x: AxisRange
    y: AxisRange

    def normalize(self, pen: PenState) -> tuple[float, float]:
        """Return the pen position as (x, y) fractions of the digitizer."""
        return self.x.normalize(pen.x), self.y.normalize(pen.y)


def _parse_axis_range(getevent_output: str, axis_name: str) -> AxisRange:
    """Extract min/max for one axis from `getevent -pl <device>` output.

    Expected line shape:
        ABS_X : value 0, min 0, max 20967, fuzz 0, flat 0, resolution 0
    """
    pattern = rf"\b{axis_name}\b\s*:\s*value\s+-?\d+,\s*min\s+(-?\d+),\s*max\s+(-?\d+)"
    if not (match := re.search(pattern, getevent_output)):
        raise RuntimeError(f"{axis_name} range not found in getevent output")
    return AxisRange(min=int(match.group(1)), max=int(match.group(2)))


def read_pen_bounds(device_node: str, serial: str | None = None) -> PenBounds:
    """Query the pen device for its ABS_X/ABS_Y ranges.

    Passing the device node to getevent limits output to that one device,
    so no block-splitting is needed here.
    """
    cmd = adb_command("shell", "getevent", "-pl", device_node, serial=serial)
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    output = result.stdout + result.stderr
    return PenBounds(
        x=_parse_axis_range(output, "ABS_X"),
        y=_parse_axis_range(output, "ABS_Y"),
    )