#!/usr/bin/env python3
"""Live terminal view of SpaceMouse axes and buttons.

Reads the device straight from Linux input events (no spacenavd needed).
Setup:  pip install evdev   (or: sudo apt install python3-evdev)
Run:    python3 cli_axis_viewer.py
If it says permission denied, run with sudo once to test, or add a udev rule.
"""
import sys
import evdev
from evdev import ecodes

NAMES = {0: "X  slide L/R", 1: "Y  slide F/B", 2: "Z  push/pull",
         3: "RX tilt     ", 4: "RY roll     ", 5: "RZ spin     "}
FULL = 350  # typical max deflection
WIDTH = 30


def find_device():
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        if any(k in dev.name.lower() for k in ("3dconnexion", "spacemouse", "spacenavigator")):
            return dev
    sys.exit("SpaceMouse not found. Check it's plugged in and you can read /dev/input/event*.")


def bar(v):
    n = int(min(abs(v), FULL) / FULL * WIDTH)
    left = " " * WIDTH if v >= 0 else " " * (WIDTH - n) + "#" * n
    right = "#" * n + " " * (WIDTH - n) if v > 0 else " " * WIDTH
    return f"[{left}|{right}]"


def draw(dev, axes, buttons):
    out = ["\033[H", f"{dev.name}  ({dev.path})   Ctrl+C to quit\n"]
    for i in range(6):
        out.append(f"{NAMES[i]} {axes[i]:+5d} {bar(axes[i])}")
    pressed = ", ".join(str(b) for b in sorted(buttons)) or "none"
    out.append(f"\nButtons: {pressed:<40}")
    print("\n".join(out), end="", flush=True)


def main():
    dev = find_device()
    axes = [0] * 6
    buttons = set()
    print("\033[2J", end="")
    draw(dev, axes, buttons)
    try:
        for ev in dev.read_loop():
            if ev.type in (ecodes.EV_REL, ecodes.EV_ABS) and ev.code < 6:
                axes[ev.code] = ev.value
            elif ev.type == ecodes.EV_KEY:
                (buttons.add if ev.value else buttons.discard)(ev.code)
            elif ev.type == ecodes.EV_SYN:
                draw(dev, axes, buttons)
    except KeyboardInterrupt:
        print("\n")


if __name__ == "__main__":
    main()
