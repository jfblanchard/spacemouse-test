# SpaceMouse

## What this is
Hobby project to learn a 3Dconnexion SpaceMouse Compact on Linux. Step one: read the six axes live. Step two: a Blender-style grid you can fly around with the puck. Later: custom tools.

## Architecture
No custom driver. The kernel's generic USB HID driver already exposes the device as a standard input device (`/dev/input/eventN`). We read those events directly with `python-evdev`. `spacenavd` (the FreeSpacenav daemon) is not used; it's only needed for apps that speak its protocol (Blender, FreeCAD).

## Key files
| File | Role |
|------|------|
| `src/cli_axis_viewer.py` | Live terminal readout of 6 axes + buttons |
| `src/grid_viewer.py` | pyglet window: Blender-style floor grid, fly/orbit with the puck |
| `src/camera.py` | Camera math (no GL): axis shaping, sign table, fly/orbit, horizon lock |
| `src/spacemouse.py` | Non-blocking evdev reader, polled once per frame |
| `70-spacemouse.rules` | udev rule granting the logged-in user read access to the device |

## How to run
```
/home/jon/mambaforge/envs/spacemouse/bin/python src/cli_axis_viewer.py
/home/jon/mambaforge/envs/spacemouse/bin/python src/grid_viewer.py
```
Env: mamba `spacemouse` (Python 3.12, evdev 2.0.0, pyglet 2.1.19). No numpy, by choice (bandwidth); vector math uses `pyglet.math`.

## Gotchas
- Device node is `root:input 0660`; `jon` isn't in `input`. Needs the udev rule installed (see header of `70-spacemouse.rules`) or the viewer fails with `Permission denied`.
- The `eventN` number can change between plugs; the viewer finds the device by name, so that's fine. Stable path: `/dev/input/by-id/usb-3Dconnexion_SpaceMouse_Compact-event-if00`.
- Device is USB `256f:c635`.
- Axis directions in `camera.SIGNS` are a best guess; flip entries there if a motion feels reversed.
- pyglet's text drawing disables GL_BLEND afterwards; re-enable it every frame before drawing.
- Grid fade must be computed per pixel (long lines make per-vertex distance wrong).
- Headless render check: `xvfb-run` works with pyglet + Mesa.

## Current status
CLI axis viewer works: all 6 axes + buttons read live (2026-10-24). Grid viewer v1 renders (checked offscreen); not yet driven with the real puck.
