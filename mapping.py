"""Map the phone's pen area onto the desktop with uniform scaling.

Mapping the pen's whole area onto the whole desktop stretches motion
whenever the two shapes differ (a 9:20 phone vs a 16:9 desktop), so the
cursor would move at different speeds along X and Y. Instead we take the
largest centered region of the pen area that has the desktop's shape: the
scale is then identical on both axes, and the whole desktop stays reachable.
"""

from __future__ import annotations

from dataclasses import dataclass

from .calibration import PenBounds

MM_PER_INCH = 25.4


@dataclass(frozen=True, slots=True)
class PhoneScreen:
    """The phone's display, which is also the pen's active area."""

    width_px: int
    height_px: int
    ppi: float

    @property
    def width_mm(self) -> float:
        return self.width_px / self.ppi * MM_PER_INCH

    @property
    def height_mm(self) -> float:
        return self.height_px / self.ppi * MM_PER_INCH


NOTE_10_LITE = PhoneScreen(width_px=1080, height_px=2400, ppi=394)


@dataclass(frozen=True, slots=True)
class DesktopScreen:
    """Desktop size in pixels (total across monitors if several are used)."""

    width: int
    height: int

    @classmethod
    def parse(cls, text: str) -> DesktopScreen:
        try:
            width, height = (int(part) for part in text.lower().split("x"))
        except ValueError:
            raise ValueError(f"expected WIDTHxHEIGHT such as 1920x1080, got {text!r}") from None
        if width <= 0 or height <= 0:
            raise ValueError(f"screen dimensions must be positive, got {text!r}")
        return cls(width, height)


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


@dataclass(frozen=True, slots=True)
class ActiveRegion:
    """Sub-rectangle of the (rotated) pen unit square that maps onto the
    whole desktop. Pen positions outside it clamp to the desktop edge."""

    left: float
    top: float
    width: float
    height: float

    def map(self, u: float, v: float) -> tuple[float, float]:
        return (
            _clamp01((u - self.left) / self.width),
            _clamp01((v - self.top) / self.height),
        )


FULL_REGION = ActiveRegion(left=0.0, top=0.0, width=1.0, height=1.0)


def oriented_size_mm(phone: PhoneScreen, rotation: int) -> tuple[float, float]:
    """Physical (width, height) of the pen area as seen after rotation."""
    if rotation in (90, 270):
        return phone.height_mm, phone.width_mm
    return phone.width_mm, phone.height_mm


def fit_region(phone: PhoneScreen, desktop: DesktopScreen, rotation: int) -> ActiveRegion:
    """Largest centered pen region with the desktop's aspect ratio."""
    width_mm, height_mm = oriented_size_mm(phone, rotation)
    pen_aspect = width_mm / height_mm
    desktop_aspect = desktop.width / desktop.height

    if pen_aspect > desktop_aspect:  # pen area is wider: trim left/right
        width, height = desktop_aspect / pen_aspect, 1.0
    else:  # pen area is taller: trim top/bottom
        width, height = 1.0, pen_aspect / desktop_aspect
    return ActiveRegion(left=(1 - width) / 2, top=(1 - height) / 2, width=width, height=height)


def px_per_mm(phone: PhoneScreen, desktop: DesktopScreen, rotation: int, region: ActiveRegion) -> float:
    """Desktop pixels the cursor travels per millimetre of pen travel
    (identical on both axes by construction)."""
    width_mm, _ = oriented_size_mm(phone, rotation)
    return desktop.width / (region.width * width_mm)


def digitizer_mismatch_warning(bounds: PenBounds, phone: PhoneScreen, tolerance: float = 0.03) -> str | None:
    """Check the digitizer's extent has the screen's shape.

    The mapping assumes the digitizer covers exactly the display; if its
    aspect differs, motion would be distorted, so say so instead of
    silently mis-scaling.
    """
    digitizer_aspect = (bounds.x.max - bounds.x.min) / (bounds.y.max - bounds.y.min)
    screen_aspect = phone.width_px / phone.height_px
    error = abs(digitizer_aspect / screen_aspect - 1)
    if error <= tolerance:
        return None
    return (
        f"digitizer aspect {digitizer_aspect:.3f} differs from the screen's "
        f"{screen_aspect:.3f} by {error:.0%}; motion may be distorted"
    )


def describe_mapping(phone: PhoneScreen, desktop: DesktopScreen, rotation: int, region: ActiveRegion) -> str:
    """Human-readable summary of the effective mapping, printed at startup."""
    lines = [
        f"Phone   : {phone.width_px}x{phone.height_px} px @ {phone.ppi:g} ppi "
        f"({phone.width_mm:.1f} x {phone.height_mm:.1f} mm)",
        f"Desktop : {desktop.width}x{desktop.height} px | rotate {rotation}",
        f"Pen area: using {region.width:.0%} x {region.height:.0%} (centered) -> "
        f"{px_per_mm(phone, desktop, rotation, region):.1f} px per mm of pen travel",
    ]
    if region.width * region.height < 0.5:
        lines.append("Tip     : most of the pen area is unused; try --rotate 90 or --rotate 270")
    return "\n".join(lines)