#!/usr/bin/env python3
"""Ring course: fly through the rings in order, against the clock.

Run:   python3 ring_course.py
Puck:  fly as in the grid viewer. The timer starts on your first move.
Buttons: left = restart level, right = next level
Keys:  R restart, N next level, 1-9 pick level, H horizon lock, Esc quit

Levels are JSON files in ../levels; best times go to ../scores.json.
"""
import json
import math
from pathlib import Path

import pyglet
from pyglet.gl import GL_DEPTH_TEST, GL_TRIANGLES, glDisable, glEnable
from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.math import Mat4, Vec3
from pyglet.window import key

from camera import WORLD_UP, shape
from grid_viewer import GridViewer
from spacemouse import BTN_LEFT, BTN_RIGHT, SpaceMouse, find_device

ROOT = Path(__file__).resolve().parent.parent
LEVEL_DIR = ROOT / "levels"
SCORE_FILE = ROOT / "scores.json"

FLY_SPEED = 8.0  # fixed so times are comparable
TUBE = 0.08      # ring tube thickness, as a fraction of ring radius

TARGET_RGB = (1.00, 0.60, 0.10)
AHEAD_RGB = (0.45, 0.55, 0.70)
DONE_RGB = (0.30, 0.60, 0.35)

RING_VERT = """#version 330 core
in vec3 position;
in vec3 normal;
uniform mat4 view_proj;
uniform mat4 model;
out vec3 v_normal;
void main() {
    gl_Position = view_proj * model * vec4(position, 1.0);
    v_normal = mat3(model) * normal;
}
"""

RING_FRAG = """#version 330 core
in vec3 v_normal;
uniform vec3 color;
out vec4 frag;
void main() {
    vec3 light = normalize(vec3(0.4, -0.5, 0.8));
    float diffuse = abs(dot(normalize(v_normal), light));
    frag = vec4(color * (0.35 + 0.65 * diffuse), 1.0);
}
"""

ARROWS = "→↗↑↖←↙↓↘"


def torus_mesh(segments=48, sides=12):
    """Unit-radius torus in the XY plane (hole along Z)."""
    pos, nrm, idx = [], [], []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        for j in range(sides):
            b = 2 * math.pi * j / sides
            cb, sb = math.cos(b), math.sin(b)
            pos += [(1 + TUBE * cb) * ca, (1 + TUBE * cb) * sa, TUBE * sb]
            nrm += [cb * ca, cb * sa, sb]
    for i in range(segments):
        for j in range(sides):
            a, b = i * sides + j, ((i + 1) % segments) * sides + j
            c, d = i * sides + (j + 1) % sides, ((i + 1) % segments) * sides + (j + 1) % sides
            idx += [a, b, d, a, d, c]
    return pos, nrm, idx


class Ring:
    def __init__(self, center, normal, radius):
        self.center, self.normal, self.radius = center, normal, radius
        u = normal.cross(WORLD_UP)
        u = u.normalize() if u.length() > 1e-6 else Vec3(1, 0, 0)
        v = normal.cross(u)
        s = radius
        self.model = Mat4(u.x * s, u.y * s, u.z * s, 0,
                          v.x * s, v.y * s, v.z * s, 0,
                          normal.x * s, normal.y * s, normal.z * s, 0,
                          center.x, center.y, center.z, 1)

    def passed(self, p0, p1):
        """True if the step p0 -> p1 crosses the ring's plane inside the hole."""
        d0 = (p0 - self.center).dot(self.normal)
        d1 = (p1 - self.center).dot(self.normal)
        if d0 == d1 or (d0 > 0) == (d1 > 0):
            return False
        hit = p0 + (p1 - p0) * (d0 / (d0 - d1))
        return (hit - self.center).length() < self.radius * (1 - TUBE)


def load_level(path):
    data = json.loads(path.read_text())
    start = data["start"]
    prev = Vec3(*start["pos"])
    rings = []
    for r in data["rings"]:
        c = Vec3(*r["pos"])
        # Ring faces the previous ring (or the start) unless the level says otherwise
        n = Vec3(*r["normal"]) if "normal" in r else c - prev
        rings.append(Ring(c, n.normalize(), r["radius"]))
        prev = c
    return {"name": data["name"], "hint": data.get("hint", ""), "file": path.stem,
            "start_pos": Vec3(*start["pos"]), "start_look": Vec3(*start["look"]), "rings": rings}


def load_scores():
    try:
        return json.loads(SCORE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class RingCourse(GridViewer):
    def __init__(self, mouse, levels):
        super().__init__(mouse, title="SpaceMouse ring course")
        self.levels = levels
        self.scores = load_scores()
        self.ring_prog = ShaderProgram(Shader(RING_VERT, "vertex"), Shader(RING_FRAG, "fragment"))
        pos, nrm, idx = torus_mesh()
        self.torus = self.ring_prog.vertex_list_indexed(len(pos) // 3, GL_TRIANGLES, idx,
                                                        position=("f", pos), normal=("f", nrm))
        self.msg = pyglet.text.Label("", font_name="monospace", font_size=18, anchor_x="center",
                                     anchor_y="center", align="center", multiline=True, width=900,
                                     color=(255, 255, 255, 230))
        self.pointer = pyglet.text.Label("", font_name="monospace", font_size=48, anchor_x="center",
                                         anchor_y="center", color=(*(int(c * 255) for c in TARGET_RGB), 255))
        self.start_level(0)

    # --- game state ---

    def start_level(self, i):
        self.level_idx = i % len(self.levels)
        lv = self.levels[self.level_idx]
        self.cam.orbit = False
        self.cam.move_speed = FLY_SPEED
        self.cam.set_pose(lv["start_pos"], lv["start_look"])
        self.target = 0
        self.elapsed = 0.0
        self.running = False
        self.finished = False
        self.new_best = False

    @property
    def level(self):
        return self.levels[self.level_idx]

    def finish(self):
        self.finished = True
        self.running = False
        key_ = self.level["file"]
        best = self.scores.get(key_)
        if best is None or self.elapsed < best:
            self.new_best = True
            self.scores[key_] = round(self.elapsed, 3)
            SCORE_FILE.write_text(json.dumps(self.scores, indent=1))

    def update(self, dt):
        for btn in self.mouse.poll():
            if btn == BTN_LEFT:
                self.start_level(self.level_idx)
            elif btn == BTN_RIGHT:
                self.start_level(self.level_idx + 1)
        if self.finished:
            return  # freeze on the finish screen
        p0 = self.cam.pos
        self.cam.update(self.mouse.axes, dt)
        if not self.running and any(shape(a) for a in self.mouse.axes):
            self.running = True
        if self.running:
            self.elapsed += dt
        rings = self.level["rings"]
        if rings[self.target].passed(p0, self.cam.pos):
            self.target += 1
            if self.target == len(rings):
                self.finish()

    def on_key_press(self, symbol, modifiers):
        if symbol == key.R:
            self.start_level(self.level_idx)
        elif symbol == key.N:
            self.start_level(self.level_idx + 1)
        elif key._1 <= symbol <= key._9 and symbol - key._1 < len(self.levels):
            self.start_level(symbol - key._1)
        elif symbol == key.H:
            self.cam.lock_horizon = not self.cam.lock_horizon
        else:
            pyglet.window.Window.on_key_press(self, symbol, modifiers)  # Esc quits; no speed keys

    # --- drawing ---

    def draw_extra(self, view_proj):
        glEnable(GL_DEPTH_TEST)
        prog = self.ring_prog
        prog.use()
        prog["view_proj"] = view_proj
        for i, ring in enumerate(self.level["rings"]):
            prog["model"] = ring.model
            prog["color"] = DONE_RGB if i < self.target else TARGET_RGB if i == self.target else AHEAD_RGB
            self.torus.draw(GL_TRIANGLES)
        prog.stop()
        glDisable(GL_DEPTH_TEST)

        cx, cy = self.width // 2, self.height // 2
        self.msg.x, self.msg.y = cx, self.height - 110  # above the rings
        self.msg.text = self.message()
        self.msg.draw()
        self.pointer.text = "" if self.finished else self.offscreen_arrow()
        self.pointer.x, self.pointer.y = cx, cy
        self.pointer.draw()

    def message(self):
        lv = self.level
        if self.finished:
            best = self.scores[lv["file"]]
            line = "NEW BEST!" if self.new_best else f"best {best:.2f} s"
            return f"Finished in {self.elapsed:.2f} s\n{line}\n\nleft button: retry   right button: next level"
        if not self.running:
            return f"Level {self.level_idx + 1}: {lv['name']}\n{lv['hint']}\n\nMove the puck to start"
        return ""

    def offscreen_arrow(self):
        """Arrow toward the next ring when it's out of view."""
        cam = self.cam
        d = self.level["rings"][self.target].center - cam.pos
        x, y, z = d.dot(cam.right), d.dot(cam.up), d.dot(cam.fwd)
        tan_v = math.tan(math.radians(30))  # half of the 60 degree vertical fov
        tan_h = tan_v * self.width / max(self.height, 1)
        if z > 0 and abs(x / z) < tan_h * 0.9 and abs(y / z) < tan_v * 0.9:
            return ""
        if z <= 0 and abs(x) < 1e-3 and abs(y) < 1e-3:
            x = 1.0  # dead behind: pick a side
        sector = round(math.atan2(y, x) / (math.pi / 4)) % 8
        return ARROWS[sector]

    def hud_text(self):
        lv, n = self.level, len(self.levels)
        best = self.scores.get(lv["file"])
        best_s = f"{best:.2f} s" if best is not None else "--"
        return (f"Level {self.level_idx + 1}/{n}: {lv['name']}   ring {self.target}/{len(lv['rings'])}\n"
                f"time {self.elapsed:6.2f} s   best {best_s}   "
                f"horizon lock: {'on' if self.cam.lock_horizon else 'off'}\n"
                f"left btn / R restart   right btn / N next   1-{n} pick level   H horizon   Esc quit")


def main():
    levels = [load_level(p) for p in sorted(LEVEL_DIR.glob("*.json"))]
    dev = find_device()
    if dev is None:
        print("SpaceMouse not found; opening anyway.")
    RingCourse(SpaceMouse(dev), levels)
    pyglet.app.run()


if __name__ == "__main__":
    main()
