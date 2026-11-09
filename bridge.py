"""Translate pen snapshots into mouse actions.

The bridge knows nothing about uinput: it talks to a `MouseSink`, so the
mapping and click logic can be tested without a real input device.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Protocol

from .calibration import PenBounds
from .mapping import FULL_REGION, ActiveRegion
from .models import PenState

ROTATIONS = (0, 90, 180, 270)

# Absolute-pointer axis range exposed by the virtual device. The desktop
# stack scales 0..ABS_MAX onto the screen, so this only needs to be finer
# than any real display (32767 is ~8.5 units per pixel on a 4K screen).
ABS_MAX = 32767


class Button(Enum):
    LEFT = auto()
    RIGHT = auto()


class MouseSink(Protocol):
    """Anything that can act as a mouse: a real uinput device or a test fake."""

    def move_to(self, x: int, y: int) -> None: ...

    def set_button(self, button: Button, pressed: bool) -> None: ...

    def sync(self) -> None: ...


def rotate_unit(u: float, v: float, rotation: int) -> tuple[float, float]:
    """Rotate a point in the unit square clockwise by `rotation` degrees.

    A true rotation (a bare X/Y swap would mirror the motion). Needed when
    the digitizer's native orientation doesn't match how you hold the phone.
    """
    match rotation:
        case 0:
            return u, v
        case 90:
            return 1 - v, u
        case 180:
            return 1 - u, 1 - v
        case 270:
            return v, 1 - u
        case _:
            raise ValueError(f"rotation must be one of {ROTATIONS}, got {rotation}")


class MouseBridge:
    """Pen -> mouse.

    - Pen position drives an absolute cursor position: the active pen region
      (see mapping.fit_region) is mapped onto the full desktop.
    - Pen tip contact (BTN_TOUCH) is the left button, so dragging works.
    - The pen's side button (BTN_STYLUS) is the right button.
    """

    def __init__(
        self,
        bounds: PenBounds,
        sink: MouseSink,
        rotation: int = 0,
        region: ActiveRegion = FULL_REGION,
    ) -> None:
        if rotation not in ROTATIONS:
            raise ValueError(f"rotation must be one of {ROTATIONS}, got {rotation}")
        self._bounds = bounds
        self._sink = sink
        self._rotation = rotation
        self._region = region
        self._pressed: set[Button] = set()

    def apply(self, pen: PenState) -> None:
        """Handle one pen report as a single atomic mouse frame.

        Move first, then change buttons, so a click always lands at the
        position carried by the same report.
        """
        u, v = rotate_unit(*self._bounds.normalize(pen), self._rotation)
        u, v = self._region.map(u, v)
        self._sink.move_to(round(u * ABS_MAX), round(v * ABS_MAX))
        self._update_buttons(self._buttons_down(pen))
        self._sink.sync()

    def release_all(self) -> None:
        """Release anything still held. Call on shutdown so a button can't stay stuck."""
        if self._pressed:
            self._update_buttons(set())
            self._sink.sync()

    @staticmethod
    def _buttons_down(pen: PenState) -> set[Button]:
        return {
            button
            for button, down in ((Button.LEFT, pen.touching), (Button.RIGHT, pen.side_button))
            if down
        }

    def _update_buttons(self, wanted: set[Button]) -> None:
        for button in self._pressed - wanted:
            self._sink.set_button(button, False)
        for button in wanted - self._pressed:
            self._sink.set_button(button, True)
        self._pressed = wanted