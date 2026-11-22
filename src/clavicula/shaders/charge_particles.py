"""Spores that puff out of the bottom third of a charging tile, then drift outward and settle downward while fading."""

from dataclasses import dataclass
from typing import Optional, Tuple

from arcade.gl import geometry

from clavicula.constants import (
    TILE_SIZE,
    PARTICLE_COLOR,
    PARTICLE_DRIFT,
    PARTICLE_FALL,
    PARTICLE_LIFE,
    PARTICLE_OPACITY,
    PARTICLE_RATE,
    PARTICLE_SIZE,
    PARTICLE_ZONE,
)

MAX_PARTICLES = 64   # must match the shader constant; PARTICLE_LIFE * PARTICLE_RATE + 2 has to fit


@dataclass
class Emitter:
    cell: Tuple[int, int]
    seed: float
    start: float
    end: Optional[float] = None      # set when the charge stops; spores already in flight keep drifting


class ChargeParticles:
    VERTEX = """
    #version 330
    in vec2 in_vert;
    in vec2 in_uv;
    out vec2 uv;
    void main() {
        gl_Position = vec4(in_vert, 0.0, 1.0);
        uv = in_uv;
    }
    """

    # Runs over the whole screen but rejects everything outside the region the
    # spores can reach. Particle j of an emitter is born at (j + jitter) / rate,
    # so the particles alive at time t are a small, known range of indices and
    # every one of them can be recomputed per pixel from hashes alone.
    FRAGMENT = """
    #version 330
    uniform vec2 u_resolution;    // window size
    uniform vec2 u_camera;        // world position at the screen centre
    uniform float u_zoom;
    uniform vec2 u_origin;        // world position of the tile's bottom-left corner
    uniform float u_tile_size;
    uniform float u_zone_height;  // spawn zone height, native px from the tile bottom
    uniform float u_cell_size;    // particle size, native px
    uniform float u_time;         // seconds since this emitter started
    uniform float u_end;          // seconds (since start) when emission stopped; huge while charging
    uniform float u_seed;
    uniform float u_life;         // seconds from birth to fully faded
    uniform float u_rate;         // particles born per second
    uniform vec2 u_fall;          // min / max total downward drift, native px
    uniform float u_drift;        // max total sideways drift, native px
    uniform float u_opacity;      // peak opacity
    uniform vec3 u_color;
    in vec2 uv;
    out vec4 frag_color;

    const int MAX_PARTICLES = 64;

    float hash13(vec3 p3) {
        p3 = fract(p3 * 0.1031);
        p3 += dot(p3, p3.zyx + 31.32);
        return fract((p3.x + p3.y) * p3.z);
    }

    void main() {
        vec2 world = u_camera + (uv * u_resolution - 0.5 * u_resolution) / u_zoom;
        vec2 px = floor(world - u_origin);     // native pixel relative to the tile

        // Cheap reject: spores spawn inside the zone and only move sideways or down.
        if (px.x < -u_drift - 1.0 || px.x > u_tile_size + u_drift ||
            px.y < -u_fall.y - 1.0 || px.y >= u_zone_height) {
            discard;
        }

        float alpha = 0.0;
        float first = floor((u_time - u_life) * u_rate);

        for (int k = 0; k < MAX_PARTICLES; k++) {
            float j = first + float(k);
            if (j > u_time * u_rate) break;
            if (j < 0.0) continue;

            vec3 key = vec3(j, u_seed, 0.0);
            float born = (j + hash13(key + vec3(0.0, 0.0, 1.0))) / u_rate;
            if (born > u_end) continue;
            float age = (u_time - born) / u_life;
            if (age < 0.0 || age >= 1.0) continue;

            // Start somewhere in the bottom third of the tile, on the pixel grid.
            float nx = u_tile_size - u_cell_size + 1.0;
            float ny = max(floor(u_zone_height - u_cell_size) + 1.0, 1.0);
            vec2 start = floor(vec2(hash13(key + vec3(0.0, 0.0, 2.0)) * nx,
                                    hash13(key + vec3(0.0, 0.0, 3.0)) * ny));

            // Drift: down by a random amount, sideways away from the tile centre.
            float fall = mix(u_fall.x, u_fall.y, hash13(key + vec3(0.0, 0.0, 4.0)));
            float side = hash13(key + vec3(0.0, 0.0, 5.0)) * 2.0 - 1.0;
            float centre = (start.x + 0.5 * u_cell_size) / u_tile_size * 2.0 - 1.0;
            float dir = clamp(0.7 * centre + 0.5 * side, -1.0, 1.0);

            // Fast start, gentle stop: the spore settles instead of coasting.
            float ease = 1.0 - (1.0 - age) * (1.0 - age);
            vec2 pos = floor(start + vec2(dir * u_drift, -fall) * ease + 0.5);

            vec2 d = px - pos;
            if (d.x >= 0.0 && d.x < u_cell_size && d.y >= 0.0 && d.y < u_cell_size) {
                float fade = smoothstep(0.0, 0.15, age) * (1.0 - age);
                alpha = max(alpha, fade);
            }
        }

        if (alpha <= 0.0) discard;
        frag_color = vec4(u_color, alpha * u_opacity);
    }
    """

    def __init__(self, window):
        assert PARTICLE_LIFE * PARTICLE_RATE + 2 <= MAX_PARTICLES, "raise MAX_PARTICLES (here and in the shader)"
        self._window = window
        self._now = 0.0
        self._emitters = []
        ctx = window.ctx
        self._quad = geometry.quad_2d_fs()
        self._program = ctx.program(
            vertex_shader=self.VERTEX, fragment_shader=self.FRAGMENT
        )
        p = self._program
        p["u_tile_size"] = float(TILE_SIZE)
        p["u_zone_height"] = TILE_SIZE * PARTICLE_ZONE
        p["u_cell_size"] = float(PARTICLE_SIZE)
        p["u_life"] = PARTICLE_LIFE
        p["u_rate"] = float(PARTICLE_RATE)
        p["u_fall"] = tuple(float(v) for v in PARTICLE_FALL)
        p["u_drift"] = float(PARTICLE_DRIFT)
        p["u_opacity"] = PARTICLE_OPACITY
        p["u_color"] = PARTICLE_COLOR

    def begin(self, cell, seed):
        """Start emitting spores from the tile at cell=(row, col). Returns a handle for end()."""
        emitter = Emitter(cell, seed, self._now)
        self._emitters.append(emitter)
        return emitter

    def end(self, emitter):
        """Stop emitting new spores; ones already in flight finish drifting."""
        if emitter.end is None:
            emitter.end = self._now

    def update(self, delta_time):
        self._now += delta_time
        self._emitters = [
            e for e in self._emitters
            if e.end is None or self._now - e.end <= PARTICLE_LIFE
        ]

    def draw(self, camera):
        if not self._emitters:
            return
        ctx = self._window.ctx
        p = self._program
        p["u_resolution"] = self._window.get_size()
        p["u_camera"] = tuple(camera.position)
        p["u_zoom"] = camera.zoom
        ctx.enable(ctx.BLEND)
        ctx.blend_func = ctx.BLEND_DEFAULT
        for e in self._emitters:
            row, col = e.cell
            p["u_origin"] = (col * TILE_SIZE, row * TILE_SIZE)
            p["u_time"] = self._now - e.start
            p["u_end"] = (e.end - e.start) if e.end is not None else 1e9
            p["u_seed"] = e.seed
            self._quad.render(p)