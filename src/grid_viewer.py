#!/usr/bin/env python3
"""Fly around a Blender-style floor grid with the SpaceMouse.

Run:   python3 grid_viewer.py
Puck:  slide = move, tilt/roll/twist = turn
Buttons: left = reset view, right = toggle fly / orbit
Keys:  R reset, M fly/orbit, H horizon lock, +/- speed, Esc quit
"""
import math
import pyglet
from pyglet.gl import (GL_BLEND, GL_LINES, GL_ONE_MINUS_SRC_ALPHA, GL_SRC_ALPHA,
                       glBlendFunc, glClearColor, glEnable)
from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.math import Mat4, Vec3
from pyglet.window import key

from camera import Camera
from spacemouse import BTN_LEFT, BTN_RIGHT, SpaceMouse, find_device

GRID_HALF = 100   # grid spans +-100 units around the camera
MAJOR = 10        # brighter line every 10 units
FADE_DIST = 60.0  # lines fade out toward this distance

VERT = """#version 330 core
in vec3 position;
in vec4 colors;
uniform mat4 view_proj;
uniform vec2 offset;
out vec4 v_color;
out vec2 v_xy;
void main() {
    vec3 p = position + vec3(offset, 0.0);
    gl_Position = view_proj * vec4(p, 1.0);
    v_color = colors;
    v_xy = p.xy;
}
"""

# Distance is measured per pixel: lines are long, so per-vertex distance would be wrong mid-line
FRAG = """#version 330 core
in vec4 v_color;
in vec2 v_xy;
uniform vec3 eye;
uniform float fade_dist;
out vec4 frag;
void main() {
    float fade = clamp(1.0 - length(v_xy - eye.xy) / fade_dist, 0.0, 1.0);
    frag = vec4(v_color.rgb, v_color.a * fade * fade);
}
"""

MINOR_RGBA = (0.33, 0.33, 0.33, 1.0)
MAJOR_RGBA = (0.45, 0.45, 0.45, 1.0)
X_RGBA = (0.90, 0.25, 0.30, 1.0)
Y_RGBA = (0.45, 0.75, 0.20, 1.0)


def grid_lines():
    pos, col = [], []
    for i in range(-GRID_HALF, GRID_HALF + 1):
        rgba = MAJOR_RGBA if i % MAJOR == 0 else MINOR_RGBA
        pos += [i, -GRID_HALF, 0, i, GRID_HALF, 0]   # parallel to Y
        pos += [-GRID_HALF, i, 0, GRID_HALF, i, 0]   # parallel to X
        col += rgba * 4
    return pos, col


def axis_lines():
    far = 10000
    pos = [-far, 0, 0, far, 0, 0, 0, -far, 0, 0, far, 0]
    col = X_RGBA * 2 + Y_RGBA * 2
    return pos, col


class GridViewer(pyglet.window.Window):
    def __init__(self, mouse, title="SpaceMouse grid"):
        try:
            config = pyglet.gl.Config(sample_buffers=1, samples=4, depth_size=24, double_buffer=True)
            super().__init__(1280, 800, title, resizable=True, config=config)
        except pyglet.window.NoSuchConfigException:
            super().__init__(1280, 800, title, resizable=True)
        self.mouse = mouse
        self.cam = Camera()
        self.program = ShaderProgram(Shader(VERT, "vertex"), Shader(FRAG, "fragment"))
        p, c = grid_lines()
        self.grid = self.program.vertex_list(len(p) // 3, GL_LINES, position=("f", p), colors=("f", c))
        p, c = axis_lines()
        self.axes = self.program.vertex_list(len(p) // 3, GL_LINES, position=("f", p), colors=("f", c))
        self.hud = pyglet.text.Label("", x=12, y=12, width=900, multiline=True, anchor_y="bottom",
                                     font_name="monospace", font_size=10, color=(220, 220, 220, 255))
        glClearColor(0.23, 0.23, 0.23, 1.0)
        pyglet.clock.schedule_interval(self.update, 1 / 120)

    def update(self, dt):
        for btn in self.mouse.poll():
            if btn == BTN_LEFT:
                self.cam.reset()
            elif btn == BTN_RIGHT:
                self.cam.toggle_mode()
        self.cam.update(self.mouse.axes, dt)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.R:
            self.cam.reset()
        elif symbol == key.M:
            self.cam.toggle_mode()
        elif symbol == key.H:
            self.cam.lock_horizon = not self.cam.lock_horizon
        elif symbol in (key.EQUAL, key.PLUS, key.NUM_ADD):
            self.cam.move_speed *= 1.5
        elif symbol in (key.MINUS, key.NUM_SUBTRACT):
            self.cam.move_speed /= 1.5
        else:
            super().on_key_press(symbol, modifiers)

    def on_draw(self):
        self.clear()
        cam = self.cam
        w, h = self.get_framebuffer_size()
        proj = Mat4.perspective_projection(w / max(h, 1), 0.05, 2000.0, fov=60)
        view = Mat4.look_at(cam.pos, cam.pos + cam.fwd, cam.up)

        # Set every frame: pyglet's text drawing disables blending when it finishes
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        prog = self.program
        prog.use()
        prog["view_proj"] = proj @ view
        prog["eye"] = cam.pos
        # See farther from higher up, but always fade out before the grid edge
        prog["fade_dist"] = min(FADE_DIST + abs(cam.pos.z) * 2, GRID_HALF * 0.9)
        # Snap the grid to the camera in MAJOR steps so it feels infinite
        prog["offset"] = (math.floor(cam.pos.x / MAJOR) * MAJOR, math.floor(cam.pos.y / MAJOR) * MAJOR)
        self.grid.draw(GL_LINES)
        prog["offset"] = (0.0, 0.0)
        self.axes.draw(GL_LINES)
        prog.stop()

        self.draw_extra(proj @ view)
        self.hud.text = self.hud_text()
        self.hud.draw()

    def draw_extra(self, view_proj):
        """Hook for subclasses: draw more 3D content after the grid."""

    def hud_text(self):
        cam, m = self.cam, self.mouse
        mode = f"orbit (dist {cam.dist:.1f})" if cam.orbit else "fly"
        dev = "  ".join(f"{a:+4d}" for a in m.axes) if m.connected else "SpaceMouse not found (keys only)"
        return (f"mode: {mode}   horizon lock: {'on' if cam.lock_horizon else 'off'}   "
                f"speed: {cam.move_speed:.1f}\n"
                f"pos: {cam.pos.x:7.2f} {cam.pos.y:7.2f} {cam.pos.z:7.2f}\n"
                f"axes: {dev}\n"
                f"R reset  M fly/orbit  H horizon  +/- speed  Esc quit")


def main():
    dev = find_device()
    if dev is None:
        print("SpaceMouse not found; opening grid anyway.")
    GridViewer(SpaceMouse(dev))
    pyglet.app.run()


if __name__ == "__main__":
    main()
