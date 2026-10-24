"""Non-blocking SpaceMouse reader on raw Linux input events (evdev)."""
import evdev
from evdev import ecodes

DEVICE_NAMES = ("3dconnexion", "spacemouse", "spacenavigator")
BTN_LEFT, BTN_RIGHT = 256, 257  # SpaceMouse Compact's two side buttons


def find_device():
    """First readable SpaceMouse, or None. Unreadable devices are skipped by evdev."""
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        if any(k in dev.name.lower() for k in DEVICE_NAMES):
            return dev
        dev.close()
    return None


class SpaceMouse:
    """Holds the latest value of each axis; poll() once per frame.

    The device only sends an axis when it changes and sends 0 on release,
    so the last value seen is the current deflection.
    """

    def __init__(self, dev):
        self.dev = dev
        self.axes = [0] * 6  # x, y, z, rx, ry, rz
        self.buttons = set()

    @property
    def connected(self):
        return self.dev is not None

    def poll(self):
        """Drain pending events. Returns button codes pressed since last poll."""
        pressed = []
        if self.dev is None:
            return pressed
        try:
            for ev in self.dev.read():
                if ev.type in (ecodes.EV_REL, ecodes.EV_ABS) and ev.code < 6:
                    self.axes[ev.code] = ev.value
                elif ev.type == ecodes.EV_KEY:
                    if ev.value:
                        self.buttons.add(ev.code)
                        pressed.append(ev.code)
                    else:
                        self.buttons.discard(ev.code)
        except BlockingIOError:
            pass  # nothing pending
        except OSError:
            self.dev = None  # unplugged
            self.axes = [0] * 6
        return pressed
