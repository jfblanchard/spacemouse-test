# SpaceMouse

## What this is
Hobby project to learn a 3Dconnexion SpaceMouse Compact on Linux. Step one: read the six axes live. Step two: a Blender-style grid you can fly around with the puck. Later: custom tools.

## Architecture
No custom driver. The kernel's generic USB HID driver already exposes the device as a standard input device (`/dev/input/eventN`). We read those events directly with `python-evdev`. `spacenavd` (the FreeSpacenav daemon) is not used; it's only needed for apps that speak its protocol (Blender, FreeCAD).

## Key files
| File | Role |
|------|------|
| `src/axis_viewer.py` | Live terminal readout of 6 axes + buttons |
| `91-spacemouse.rules` | udev rule granting the logged-in user read access to the device |

## How to run
```
/home/jon/mambaforge/envs/spacemouse/bin/python src/axis_viewer.py
```
Env: mamba `spacemouse` (Python 3.12, evdev 2.0.0).

## Gotchas
- Device node is `root:input 0660`; `jon` isn't in `input`. Needs the udev rule installed (see header of `91-spacemouse.rules`) or the viewer fails with `Permission denied`.
- The `eventN` number can change between plugs; the viewer finds the device by name, so that's fine. Stable path: `/dev/input/by-id/usb-3Dconnexion_SpaceMouse_Compact-event-if00`.
- Device is USB `256f:c635`.

## Current status
Axis viewer written, untested on hardware pending the udev rule. Grid viewer not started.
