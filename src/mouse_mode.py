#!/usr/bin/env python3
"""Use the SpaceMouse as a regular mouse while this runs. Ctrl+C to stop.

Slide = move cursor, twist = scroll, left/right buttons = left/right click.
Creates a virtual mouse through /dev/uinput, so it works in any app (X11 or Wayland).
"""
import sys
import time

from evdev import UInput, ecodes

from camera import shape
from spacemouse import BTN_LEFT, BTN_RIGHT, SpaceMouse, find_device

CURSOR_SPEED = 1500  # pixels/s at full deflection
SCROLL_SPEED = 12    # wheel notches/s at full twist
RATE = 120           # updates/s

CLICKS = {BTN_LEFT: ecodes.BTN_LEFT, BTN_RIGHT: ecodes.BTN_RIGHT}


class WriteOnlyUInput(UInput):
    """Skips evdev's lookup of the new device node: we only write, and the node
    isn't readable without root, so the lookup just stalls startup for ~2 s."""

    def _find_device(self, fd):
        return None


def main():
    dev = find_device()
    if dev is None:
        sys.exit("SpaceMouse not found.")
    mouse = SpaceMouse(dev)
    caps = {ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL],
            ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT]}
    try:
        ui = WriteOnlyUInput(caps, name="SpaceMouse virtual mouse")
    except PermissionError:
        sys.exit("No write access to /dev/uinput (needs a uaccess udev rule).")

    print("Mouse mode on. Ctrl+C to stop.")
    dt = 1 / RATE
    held = set()
    rem_x = rem_y = rem_wheel = 0.0  # carry fractions so slow motion still moves
    try:
        while True:
            mouse.poll()
            if not mouse.connected:
                sys.exit("SpaceMouse unplugged.")
            x, y, _, _, _, rz = mouse.axes

            rem_x += shape(x) * CURSOR_SPEED * dt
            rem_y += shape(y) * CURSOR_SPEED * dt
            rem_wheel += -shape(rz) * SCROLL_SPEED * dt  # twist sign: flip if scroll feels reversed
            dx, dy, wheel = int(rem_x), int(rem_y), int(rem_wheel)
            rem_x, rem_y, rem_wheel = rem_x - dx, rem_y - dy, rem_wheel - wheel
            if dx:
                ui.write(ecodes.EV_REL, ecodes.REL_X, dx)
            if dy:
                ui.write(ecodes.EV_REL, ecodes.REL_Y, dy)
            if wheel:
                ui.write(ecodes.EV_REL, ecodes.REL_WHEEL, wheel)

            for btn, click in CLICKS.items():
                down = btn in mouse.buttons
                if down != (btn in held):
                    ui.write(ecodes.EV_KEY, click, int(down))
                    (held.add if down else held.discard)(btn)

            ui.syn()
            time.sleep(dt)
    except KeyboardInterrupt:
        print("\nMouse mode off.")
    finally:
        for btn in held:  # never leave a button stuck down
            ui.write(ecodes.EV_KEY, CLICKS[btn], 0)
        ui.syn()
        ui.close()


if __name__ == "__main__":
    main()
