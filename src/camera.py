"""6-DOF camera driven by SpaceMouse axes. World is Z-up, like Blender.

Pure math, no OpenGL, so it can be tested without a window.
"""
import math
from pyglet.math import Vec3

WORLD_UP = Vec3(0, 0, 1)

# Puck tuning
FULL = 300       # deflection treated as full speed (device nominal is ~350)
DEADZONE = 15    # ignore tiny values so the view doesn't drift at rest
CURVE = 2.0      # >1 gives finer control near center

# Per-axis sign: flip any that move the wrong way. Order: x, y, z, rx, ry, rz.
SIGNS = (1, -1, -1, 1, -1, -1)

HOME_POS = Vec3(10, -10, 6)
HOME_TARGET = Vec3(0, 0, 0)


def shape(v):
    """Raw axis value -> -1..1 with deadzone and response curve."""
    mag = (abs(v) - DEADZONE) / (FULL - DEADZONE)
    if mag <= 0:
        return 0.0
    return math.copysign(min(mag, 1.0) ** CURVE, v)


def rotate(v, axis, angle):
    """Rotate v about unit vector axis by angle (Rodrigues)."""
    c, s = math.cos(angle), math.sin(angle)
    return v * c + axis.cross(v) * s + axis * (axis.dot(v) * (1 - c))


class Camera:
    def __init__(self):
        self.move_speed = 6.0                 # units/s at full deflection
        self.turn_speed = math.radians(90)    # rad/s at full deflection
        self.orbit = False
        self.lock_horizon = False  # H toggles; on = level floor, roll ignored
        self.reset()

    def reset(self):
        self.pos = HOME_POS
        self.fwd = (HOME_TARGET - HOME_POS).normalize()
        self._rebuild_basis(WORLD_UP)
        self.pivot = HOME_TARGET
        self.dist = (HOME_TARGET - HOME_POS).length()

    def _rebuild_basis(self, up_hint):
        """Re-orthonormalize right/up from fwd, keeping up close to up_hint."""
        self.right = self.fwd.cross(up_hint).normalize()
        self.up = self.right.cross(self.fwd).normalize()

    def toggle_mode(self):
        self.orbit = not self.orbit
        if self.orbit:
            # Pivot where the view ray meets the floor, or 10 units ahead
            if self.fwd.z < -0.05:
                self.dist = min(max(-self.pos.z / self.fwd.z, 1.0), 200.0)
            else:
                self.dist = 10.0
            self.pivot = self.pos + self.fwd * self.dist

    def update(self, axes, dt):
        tx, ty, tz, rx, ry, rz = (shape(a) * s for a, s in zip(axes, SIGNS))
        # Mapping: tx strafe right, ty forward, tz up, rx pitch, ry roll, rz yaw
        pitch, roll, yaw = (r * self.turn_speed * dt for r in (rx, ry, rz))

        # Rotation: pitch about right, yaw about up (or world up when level), roll about fwd
        yaw_axis = WORLD_UP if self.lock_horizon else self.up
        self.fwd = rotate(self.fwd, yaw_axis, -yaw)
        if not self.lock_horizon or abs(rotate(self.fwd, self.right, pitch).z) < 0.995:
            self.fwd = rotate(self.fwd, self.right, pitch)
        if self.lock_horizon:
            self._rebuild_basis(WORLD_UP)
        else:
            up = rotate(rotate(self.up, yaw_axis, -yaw), self.right, pitch)
            up = rotate(up, self.fwd, roll)
            self._rebuild_basis(up)

        if self.orbit:
            # Strafe/rise pans the pivot (scaled by distance), forward dollies in/out
            pan = self.move_speed * dt * self.dist / 10
            self.pivot += (self.right * tx + self.up * tz) * pan
            self.dist = min(max(self.dist * math.exp(-ty * dt * 1.5), 0.5), 500.0)
            self.pos = self.pivot - self.fwd * self.dist
        else:
            step = self.move_speed * dt
            self.pos += (self.right * tx + self.fwd * ty + self.up * tz) * step
