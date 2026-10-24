# Dev notes

## 2026-10-22
- Device detected as `3Dconnexion SpaceMouse Compact`, event24. Permission denied reading it: `jon` not in `input` group.
- Wrote udev rule using `uaccess` tag (seat-user ACL, no group change or logout needed).
- Created mamba env `spacemouse`, installed evdev.

## 2026-10-24
- Moved from /mnt/data/projects to /mnt/data/hobby. Added lean structure (src/, docs/ logs, core md files). Skipped tests/, validation/, design/, research/ until they earn a place.
- Decision: read evdev directly, no spacenavd.
