# Lessons learned

- A SpaceMouse needs no custom driver on Linux: the kernel exposes it as an evdev device. The only hurdle is permissions on `/dev/input/eventN`.
