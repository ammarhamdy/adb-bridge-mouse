"""Raw evdev byte-stream -> RawEvent generator."""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from typing import Iterator

from .adb import adb_command, detect_abi
from .models import RawEvent
from .protocol import struct_for_abi


@contextmanager
def _adb_cat_process(device_node: str, serial: str | None = None) -> Iterator[subprocess.Popen]:
    """Open `adb exec-out cat <device_node>` as a clean binary pipe.

    exec-out (not `shell`) avoids the pty line-ending/buffering translation
    that would corrupt a binary event stream. The process is terminated
    *and reaped* on exit, so an early-stopped consumer doesn't leave a
    zombie adb/cat process behind.
    """
    cmd = adb_command("exec-out", "cat", device_node, serial=serial)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
    try:
        yield proc
    finally:
        proc.terminate()
        proc.wait()


def raw_event_stream(device_node: str, serial: str | None = None) -> Iterator[RawEvent]:
    """Yield RawEvents forever from a device's raw binary evdev stream."""
    event_struct = struct_for_abi(detect_abi(serial))

    with _adb_cat_process(device_node, serial) as proc:
        assert proc.stdout is not None
        buf = b""
        while chunk := proc.stdout.read(event_struct.size * 64):
            buf += chunk
            while len(buf) >= event_struct.size:
                raw, buf = buf[: event_struct.size], buf[event_struct.size :]
                _, _, ev_type, ev_code, ev_value = event_struct.unpack(raw)
                yield RawEvent(ev_type, ev_code, ev_value)