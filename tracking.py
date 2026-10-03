"""Fold raw event streams into structured per-contact snapshots."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterator

from .models import Finger, PenState, RawEvent
from .protocol import AbsCode, EventType, KeyCode, SynCode


def track_fingers(events: Iterator[RawEvent]) -> Iterator[dict[int, Finger]]:
    """Fold the touchscreen event stream into per-SYN_REPORT snapshots of
    active fingers, keyed by MT slot (Protocol B multitouch).

    Each snapshot copies its Finger objects (via dataclasses.replace)
    rather than sharing references with the live state, so a consumer that
    buffers past snapshots doesn't see them mutate retroactively as later
    events update the finger that's still in the same slot.
    """
    fingers: dict[int, Finger] = {}
    slot = 0

    for ev in events:
        match ev.type, ev.code:
            case EventType.ABS, AbsCode.MT_SLOT:
                slot = ev.value
            case EventType.ABS, AbsCode.MT_TRACKING_ID:
                if ev.value == -1:
                    fingers.pop(slot, None)
                elif slot in fingers:
                    fingers[slot].tracking_id = ev.value
                else:
                    fingers[slot] = Finger(slot=slot, tracking_id=ev.value)
            case EventType.ABS, AbsCode.MT_POSITION_X if slot in fingers:
                fingers[slot].x = ev.value
            case EventType.ABS, AbsCode.MT_POSITION_Y if slot in fingers:
                fingers[slot].y = ev.value
            case EventType.SYN, SynCode.REPORT:
                yield {s: replace(f) for s, f in fingers.items()}


def track_stylus(events: Iterator[RawEvent]) -> Iterator[PenState]:
    """Fold the S-Pen event stream into per-SYN_REPORT PenState snapshots.

    Single contact point, no MT slots. BTN_TOOL_PEN toggles on when the pen
    enters hover range; BTN_TOUCH toggles on when the tip makes contact;
    BTN_STYLUS is the pen's side/barrel button. ABS_DISTANCE/ABS_PRESSURE
    are optional depending on digitizer firmware — and so, on some
    drivers, is BTN_TOOL_PEN itself: if a device never emits it, `hovering`
    simply stays False for that device, since there's no proximity signal
    to read.
    """
    state = PenState()

    for ev in events:
        match ev.type, ev.code:
            case EventType.KEY, KeyCode.TOOL_PEN:
                state.hovering = bool(ev.value)
            case EventType.KEY, KeyCode.TOUCH:
                state.touching = bool(ev.value)
            case EventType.KEY, KeyCode.STYLUS:
                state.side_button = bool(ev.value)
            case EventType.ABS, AbsCode.X:
                state.x = ev.value
            case EventType.ABS, AbsCode.Y:
                state.y = ev.value
            case EventType.ABS, AbsCode.PRESSURE:
                state.pressure = ev.value
            case EventType.ABS, AbsCode.DISTANCE:
                state.distance = ev.value
            case EventType.SYN, SynCode.REPORT:
                yield replace(state)