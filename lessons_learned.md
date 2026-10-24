# Lessons learned

- A SpaceMouse needs no custom driver on Linux: the kernel exposes it as an evdev device. The only hurdle is permissions on `/dev/input/eventN`.
- udev `uaccess` rules must be numbered below 73 (e.g. `70-*.rules`). `73-seat-late.rules` is what converts the tag into a user ACL; a `91-*` rule sets the tag afterwards and nothing happens. Symptom: `udevadm info` shows `TAGS=:uaccess:` but `getfacl` shows no `user:jon` entry.
