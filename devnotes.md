# Dev notes

## 2026-10-22
- Device detected as `3Dconnexion SpaceMouse Compact`, event24. Permission denied reading it: `jon` not in `input` group.
- Wrote udev rule using `uaccess` tag (seat-user ACL, no group change or logout needed).
- Created mamba env `spacemouse`, installed evdev.

## 2026-10-24
- Moved from /mnt/data/projects to /mnt/data/hobby. Added lean structure (src/, docs/ logs, core md files). Skipped tests/, validation/, design/, research/ until they earn a place.
- Decision: read evdev directly, no spacenavd.
- Rule installed as 91-spacemouse.rules: tag applied, no ACL. Cause: uaccess is processed in 73-seat-late.rules, so the rule must sort before it. Renamed to 70-spacemouse.rules.
- Moved with bare mv before safe-move policy existed; `safe-move scan` shows only historical log references to the old path.
- Viewer confirmed working on hardware. Device reports EV_REL axes 0-5 (no absinfo, so no declared min/max), buttons 256/257, one LED. Jon sees ~300 at full deflection; 3Dconnexion nominal is ±350.
- Renamed axis_viewer.py -> src/cli_axis_viewer.py.
- Chose pyglet over moderngl (one dependency, camera math stays ours). Skipped numpy to save bandwidth.
- Built grid_viewer.py + camera.py + spacemouse.py. Z-up world, red X / green Y axes, grid snaps to camera in 10-unit steps so it feels infinite, distance fade.
- Controls: fly (move along view, horizon lock default) and orbit (pivot where view meets floor; push/pull dollies). Left button reset, right button toggles mode. Keys R/M/H/+/-.
- Debugged two render bugs offscreen with xvfb: label disables blending, and per-vertex fade distance on 200-unit lines.
- Renamed to spacemouse-test (folder + GitHub repo, private). docs/ untracked and stripped from history; personal logs now in global gitignore.
- Pitch sign flipped: pulling the puck back now pitches the view up (flight-stick feel).
- Roll is ignored while horizon lock is on; H toggles it.
- Added mouse_mode.py (uinput virtual mouse, foreground, Ctrl+C off) and README with screenshot + SVG axis diagram.
- Horizon lock now defaults off so roll works out of the box (Jon expected roll about the view axis). Verified: roll rotates up 90 deg/s about fwd, fwd unchanged.
- Ring course v1 (src/ring_course.py): subclass of GridViewer, torus mesh with simple lighting and depth test, pass check = segment crosses ring plane inside the hole (either direction), only the current target counts. 3 JSON levels (straight, slalom, spiral climb). Fixed FLY_SPEED 8 for fair times. Verified with scripted runs under xvfb: L1 full throttle = 9.00 s (72 units / 8).
- Godot rev 2 planned as its own repo, reusing levels/*.json.
