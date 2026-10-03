# adb_bridge_mouse

A small Python project that reads touch and S-Pen input from an Android device over ADB and exposes it as simple event data.

This project is useful when you want to understand what the phone is sending from its touchscreen or pen digitizer. It does not draw a UI or control the computer directly; instead, it reads raw Android input events and turns them into easy-to-use Python objects.

## What this project does

The program:

- finds the phone's touchscreen device via `adb`
- finds the S-Pen / stylus device via `adb`
- reads raw Linux input events from `/dev/input/event*`
- decodes those events into structured data
- tracks finger touches and pen movement
- prints the resulting snapshots in real time

In simple terms: it turns Android screen input into Python-friendly data.

## Why this exists

The project is meant for experiments and input-stream processing. It is useful for:

- studying Android touch input
- tracking finger positions from a phone screen
- watching pen hover/touch events
- building custom input pipelines on top of Android devices

## How it works

The project is split into a few small parts:

- `__main__.py` — command-line entry point
- `adb.py` — finds Android devices and prepares ADB commands
- `protocol.py` — knows the Linux input-event format
- `stream.py` — reads raw binary input data from the device
- `tracking.py` — turns raw events into finger/pen snapshots
- `models.py` — data classes for finger and pen state
- `capture.py` — combines touch and pen streams into one output stream

The key idea is simple:

1. use ADB to access the Android device
2. read the raw input event stream from the device node
3. decode the event fields
4. track active fingers and pen state
5. emit snapshots that can be consumed by another program

## Requirements

Before running this project, make sure you have:

- Python installed
- `adb` installed and available in your PATH
- an Android device connected to your computer
- USB debugging enabled on the phone

You may also need to authorize your computer in the phone's ADB trust dialog.

## Installation

Clone the project and run it from the project folder:

```bash
git clone <your-repo-url>
cd adb_bridge_mouse
python -m adb_bridge_mouse
```

If you have multiple Android devices connected, you can choose one with:

```bash
python -m adb_bridge_mouse --serial YOUR_DEVICE_SERIAL
```

## Example usage

```bash
python -m adb_bridge_mouse
```

The script will start printing events like:

```text
finger {'slot': 0, 'tracking_id': 12, 'x': 320, 'y': 540}
pen PenState(x=310, y=440, pressure=50, distance=0, hovering=False, touching=True, side_button=False)
```

The exact output depends on the device and the input being generated.

## Project structure

```text
adb_bridge_mouse/
├── __main__.py        # program entry point
├── adb.py             # adb helpers and input-device detection
├── capture.py        # combines touch + pen capture
├── init.py           # package export surface
├── models.py         # dataclasses used by the pipeline
├── protocol.py       # Linux evdev protocol constants
├── stream.py         # reads raw device events over adb
├── tracking.py       # converts raw events into meaningful snapshots
└── README.md         # project documentation
```

## Notes

- This project reads device input directly and works best on Android devices that expose the relevant input nodes.
- Some devices may hide or restrict input nodes, so you may need to troubleshoot ADB permissions or device drivers.
- This project is a low-level utility and is meant to be used as a building block for other input tools.

## Summary

This project is a simple Android input bridge: it uses `adb` to watch the phone's touchscreen and stylus events, converts raw Linux input data into structured Python objects, and makes those events available for further processing.
