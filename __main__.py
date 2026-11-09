"""CLI entry point: `python -m adb_bridge_mouse [--serial SERIAL]`."""

    
"""CLI entry point: `python3 -m adb_bridge_mouse [--serial S] [--rotate N]`.

Drives the desktop cursor from the S-Pen through a virtual uinput mouse.
Stop with Ctrl+C.
"""


"""CLI entry point: `python3 -m adb_bridge_mouse [--screen WxH] [--rotate N] [--serial S]`.

Drives the desktop cursor from the S-Pen through a virtual uinput mouse.
Stop with Ctrl+C.
"""

import argparse
import sys

from .adb import find_stylus_device
from .bridge import ROTATIONS, MouseBridge
from .calibration import read_pen_bounds
from .mapping import (
    NOTE_10_LITE,
    DesktopScreen,
    describe_mapping,
    digitizer_mismatch_warning,
    fit_region,
)
from .stream import raw_event_stream
from .tracking import track_stylus

DEFAULT_DESKTOP = DesktopScreen(1920, 1080)

UINPUT_HELP = """\
Could not create the virtual mouse: {error}

One-time setup so your normal user can open /dev/uinput (don't run this
whole tool with sudo: adb would start a root server that isn't authorized
for your phone):

    sudo modprobe uinput
    echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' \\
        | sudo tee /etc/udev/rules.d/99-uinput.rules
    sudo udevadm control --reload-rules && sudo udevadm trigger
    sudo usermod -aG input "$USER"      # then log out and back in
"""


def _desktop_arg(text: str) -> DesktopScreen:
    try:
        return DesktopScreen.parse(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def main() -> None:
    parser = argparse.ArgumentParser(description="Control the desktop mouse with the S-Pen.")
    parser.add_argument("--serial", help="adb device serial (only needed with multiple devices)")
    parser.add_argument(
        "--screen", type=_desktop_arg, default=DEFAULT_DESKTOP, metavar="WxH",
        help="desktop size in pixels, total across monitors if you use several "
             "(default: 1920x1080). Only its shape matters, for uniform X/Y sensitivity.",
    )
    parser.add_argument(
        "--rotate", type=int, choices=ROTATIONS, default=0,
        help="rotate pen motion clockwise; 90/270 suit a phone lying landscape",
    )
    args = parser.parse_args()

    try:
        from evdev import UInputError

        from .uinput_mouse import UInputMouse
    except ImportError:
        raise SystemExit("Missing dependency. Install it with: sudo apt install python3-evdev")

    device_node = find_stylus_device(args.serial)
    bounds = read_pen_bounds(device_node, args.serial)

    phone = NOTE_10_LITE
    region = fit_region(phone, args.screen, args.rotate)
    if warning := digitizer_mismatch_warning(bounds, phone):
        print(f"Warning: {warning}", file=sys.stderr)

    try:
        mouse = UInputMouse()
    except UInputError as error:
        raise SystemExit(UINPUT_HELP.format(error=error))

    with mouse:
        bridge = MouseBridge(bounds, mouse, args.rotate, region)
        print(describe_mapping(phone, args.screen, args.rotate, region))
        print(f"Pen {device_node} -> mouse. Ctrl+C to stop.")
        try:
            for pen in track_stylus(raw_event_stream(device_node, args.serial)):
                bridge.apply(pen)
        except KeyboardInterrupt:
            pass
        finally:
            bridge.release_all()


if __name__ == "__main__":
    main()
    

# python3 -m adb_bridge_mouse
# python3 -m adb_bridge_mouse --rotate 90 --screen 1920x1080
# python3 -m adb_bridge_mouse --rotate 270 --screen 1920x1080
