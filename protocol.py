"""Linux evdev protocol constants and the raw input_event wire format.

Single responsibility: know how Android's kernel input layer represents
events on the wire, so other modules never touch raw hex codes directly.
"""

from __future__ import annotations

import struct
from enum import IntEnum


class EventType(IntEnum):
    """`type` field of struct input_event (see <linux/input-event-codes.h>)."""

    SYN = 0x00
    KEY = 0x01
    ABS = 0x03


class SynCode(IntEnum):
    """`code` values valid when type == EventType.SYN."""

    REPORT = 0x00


class KeyCode(IntEnum):
    """`code` values valid when type == EventType.KEY."""
 
    TOUCH = 0x14A
    TOOL_PEN = 0x140
    STYLUS = 0x14B


class AbsCode(IntEnum):
    """`code` values valid when type == EventType.ABS."""

    X = 0x00
    Y = 0x01
    PRESSURE = 0x18
    DISTANCE = 0x19
    MT_SLOT = 0x2F
    MT_POSITION_X = 0x35
    MT_POSITION_Y = 0x36
    MT_TRACKING_ID = 0x39


# `struct input_event` layout differs by pointer width:
#   64-bit (arm64 — virtually all modern Android): 2x int64 time + 2x uint16 + int32 = 24 bytes
#   32-bit (legacy/rare):                          2x int32 time + 2x uint16 + int32 = 16 bytes
# '=' forces standard sizes with no compiler padding.
INPUT_EVENT_64 = struct.Struct("=qqHHi")
INPUT_EVENT_32 = struct.Struct("=iiHHi")


def struct_for_abi(abi: str) -> struct.Struct:
    """Pick the input_event wire format matching a `ro.product.cpu.abi` value."""
    return INPUT_EVENT_64 if "64" in abi else INPUT_EVENT_32