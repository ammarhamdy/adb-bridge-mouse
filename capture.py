"""Concurrent touchscreen + S-Pen capture, merged into one ordered stream."""

from __future__ import annotations

import queue
import threading
from typing import Iterator

from .adb import find_stylus_device, find_touchscreen_device
from .stream import raw_event_stream
from .tracking import track_fingers, track_stylus

Snapshot = tuple[str, object]


def _pump(label: str, snapshots: Iterator[object], sink: "queue.Queue[Snapshot]") -> None:
    """Push (label, snapshot) pairs from one device's snapshot stream into
    the shared queue. Runs in its own thread — see capture_both()."""
    for snapshot in snapshots:
        sink.put((label, snapshot))


def capture_both(serial: str | None = None) -> Iterator[Snapshot]:
    """Capture touchscreen and S-Pen concurrently and yield merged,
    time-ordered (source_label, snapshot) pairs.

    Two independent `adb exec-out` connections run in separate threads
    because each is reading an infinite character-device stream — they
    can't share one `cat` invocation the way regular files could.
    """
    sources = {
        "finger": track_fingers(raw_event_stream(find_touchscreen_device(serial), serial)),
        "pen": track_stylus(raw_event_stream(find_stylus_device(serial), serial)),
    }

    sink: "queue.Queue[Snapshot]" = queue.Queue()
    for label, snapshots in sources.items():
        threading.Thread(target=_pump, args=(label, snapshots, sink), daemon=True).start()

    while True:
        yield sink.get()