"""CLI entry point: `python -m adb_bridge_mouse [--serial SERIAL]`."""

from __future__ import annotations

import argparse

from .capture import capture_both


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream Android touch + S-Pen events over adb.")
    parser.add_argument("--serial", help="adb device serial (only needed with multiple devices attached)")
    args = parser.parse_args()

    for source, snapshot in capture_both(args.serial):
        print(source, snapshot)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting on Ctrl-C")
    

# python3 -m adb_bridge_mouse
