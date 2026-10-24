# Lessons learned

- A SpaceMouse needs no custom driver on Linux: the kernel exposes it as an evdev device. The only hurdle is permissions on `/dev/input/eventN`.
- udev `uaccess` rules must be numbered below 73 (e.g. `70-*.rules`). `73-seat-late.rules` is what converts the tag into a user ACL; a `91-*` rule sets the tag afterwards and nothing happens. Symptom: `udevadm info` shows `TAGS=:uaccess:` but `getfacl` shows no `user:jon` entry.
- pyglet text labels leave GL_BLEND disabled after drawing. Custom GL drawing that relies on alpha must enable blending each frame, not once at startup.
- Distance fades on long line segments must be computed in the fragment shader. Per-vertex distance gets linearly interpolated between the two far endpoints, so the middle of a line near the camera still reads as "far".
- Probing shaders by multiplying a term by 0.0 lets the compiler remove it and its uniforms, which then raise KeyError in pyglet. Use every probed value in the output.
