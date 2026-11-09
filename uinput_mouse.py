"""A virtual absolute-pointer mouse backed by Linux uinput.

uinput works at the kernel level, so unlike xdotool-style tools it behaves
the same under X11 and Wayland. Requires python-evdev and write access to
/dev/uinput.
"""

from __future__ import annotations

from types import TracebackType

from evdev import AbsInfo, UInput, ecodes

from .bridge import ABS_MAX, Button

DEVICE_NAME = "adb-bridge-pen"

_BUTTON_CODES = {
    Button.LEFT: ecodes.BTN_LEFT,
    Button.RIGHT: ecodes.BTN_RIGHT,
}


def device_capabilities() -> dict:
    """Capabilities for an absolute pointer: ABS_X/ABS_Y plus two buttons.

    Deliberately omits BTN_TOUCH / BTN_STYLUS / BTN_TOOL_PEN: with those the
    desktop would classify this as a touchscreen or graphics tablet instead
    of a plain absolute mouse.
    """
    axis = AbsInfo(value=0, min=0, max=ABS_MAX, fuzz=0, flat=0, resolution=0)
    return {
        ecodes.EV_KEY: list(_BUTTON_CODES.values()),
        ecodes.EV_ABS: [(ecodes.ABS_X, axis), (ecodes.ABS_Y, axis)],
    }


class UInputMouse:
    """MouseSink implementation; use as a context manager so the virtual
    device is always destroyed on exit."""

    def __init__(self, name: str = DEVICE_NAME) -> None:
        self._device = UInput(device_capabilities(), name=name)

    def move_to(self, x: int, y: int) -> None:
        self._device.write(ecodes.EV_ABS, ecodes.ABS_X, x)
        self._device.write(ecodes.EV_ABS, ecodes.ABS_Y, y)

    def set_button(self, button: Button, pressed: bool) -> None:
        self._device.write(ecodes.EV_KEY, _BUTTON_CODES[button], int(pressed))

    def sync(self) -> None:
        self._device.syn()

    def close(self) -> None:
        self._device.close()

    def __enter__(self) -> UInputMouse:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()