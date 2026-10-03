"""Dataclasses shared across the capture pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RawEvent:
    """One decoded struct input_event."""

    type: int
    code: int
    value: int


@dataclass(slots=True)
class Finger:
    """One active multitouch contact (Protocol B)."""

    slot: int
    tracking_id: int
    x: int = 0
    y: int = 0


@dataclass(slots=True)
class PenState:
    """Snapshot of the S-Pen's single contact point."""

    x: int = 0
    y: int = 0
    pressure: int = 0
    distance: int = 0
    hovering: bool = False
    touching: bool = False
    side_button: bool = False