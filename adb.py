"""adb process helpers and input-device discovery."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence


def adb_command(*args: str, serial: str | None = None) -> list[str]:
    """Build an `adb` argv, optionally pinned to one device via -s."""
    return ["adb", *(["-s", serial] if serial else []), *args]


def detect_abi(serial: str | None = None) -> str:
    """Return the device's `ro.product.cpu.abi` property."""
    cmd = adb_command("shell", "getprop", "ro.product.cpu.abi", serial=serial)
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _parse_device_blocks(output: str) -> list[tuple[str, str, str]]:
    """Split `getevent -pl` output into (path, name, block_text) tuples.

    A device missing from this list entirely (rather than just missing a
    capability) usually means adb couldn't open it at all — commonly a
    "could not get driver version ... Permission denied" line for that
    node, which getevent prints instead of an "add device" block.
    """
    blocks = re.split(r"(?=^add device)", output, flags=re.MULTILINE)
    parsed: list[tuple[str, str, str]] = []
    for block in blocks:
        if not (path_match := re.match(r"add device \d+: (/dev/input/event\d+)", block)):
            continue
        name_match = re.search(r'name:\s*"(.*)"', block)
        name = name_match.group(1) if name_match else "<unknown>"
        parsed.append((path_match.group(1), name, block))
    return parsed


def _find_device_by_capability(markers: Sequence[str], serial: str | None = None) -> str:
    """Return the /dev/input/eventX path of the first device whose
    `getevent -pl` block contains any of `markers`.

    Accepts multiple markers because not every digitizer driver reports
    the same capability for the same physical feature — e.g. some pen
    digitizers expose BTN_STYLUS instead of, or alongside, BTN_TOOL_PEN.
    On failure, lists every device getevent *did* see, since "device not
    found" and "device found but missing this capability" need different
    fixes and previously looked identical.
    """
    cmd = adb_command("shell", "getevent", "-pl", serial=serial)
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    output = result.stdout + result.stderr  # permission errors can land on either

    devices = _parse_device_blocks(output)
    for path, _, block in devices:
        if any(marker in block for marker in markers):
            return path

    seen = "\n".join(f"  {path}  ({name})" for path, name, _ in devices) or "  (none listed)"
    raise RuntimeError(
        f"No input device exposing any of {list(markers)} found.\n"
        f"Devices seen via `adb shell getevent -pl`:\n{seen}\n"
        "If the device you expect is missing from that list entirely (not "
        "just missing the capability), check for a 'Permission denied' "
        "line — some digitizer nodes are restricted to a group the adb "
        "shell user isn't in, which hides them from this listing."
    )


def find_touchscreen_device(serial: str | None = None) -> str:
    """Locate the capacitive touchscreen (Protocol B multitouch) node."""
    return _find_device_by_capability(["ABS_MT_POSITION_X"], serial)


def find_stylus_device(serial: str | None = None) -> str:
    """Locate the S-Pen / stylus digitizer node."""
    return _find_device_by_capability(["BTN_TOOL_PEN", "BTN_STYLUS"], serial)