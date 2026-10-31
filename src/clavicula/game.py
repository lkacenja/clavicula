"""
Platformer Game

python -m arcade.examples.platform_tutorial.01_open_window
"""

import math
from typing import Dict, Tuple

import arcade
from arcade.future.light.light_demo_perf import SCREEN_WIDTH, SCREEN_HEIGHT

from clavicula.data.grid import TypedGrid, MutationEvent, TileType
from clavicula.data.ascii_loader import load_ascii
from pyglet.gl import GL_NEAREST
from arcade.gl import geometry

# Constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Clavicula"
CHARACTER_SCALE = 1
CAMERA_ZOOM = 2
TILE_SIZE = 16
TILESET_PATH: str = "./src/clavicula/assets/tiles.png"
CHAR_SPRITE_PATH: str = "./src/clavicula/assets/cla-char-sized.png"

TILESET_COLUMNS = 5

TILE_INDEX: Dict[TileType, int] = {
    TileType.EMPTY: 0,
    TileType.MUTABLE_PERMANENT: 1,
    TileType.MUTABLE_DECAY: 2,
    TileType.IMMUTABLE: 4,
}

_sheet = arcade.SpriteSheet(TILESET_PATH)
_tile_textures = _sheet.get_texture_grid(
    size=(TILE_SIZE, TILE_SIZE),
    columns=TILESET_COLUMNS,
    count=max(TILE_INDEX.values()) + 1,
)

_TEXTURE_BY_TYPE: Dict[TileType, arcade.Texture] = {
    tile_type: _tile_textures[index] for tile_type, index in TILE_INDEX.items()
}


class GridRenderer:
    def __init__(self):
        self.rows = math.ceil(WINDOW_HEIGHT / TILE_SIZE)
        self.cols = math.ceil(WINDOW_WIDTH / TILE_SIZE)
        self.grid: TypedGrid[TileType] = TypedGrid(
            self.rows, self.cols, default=TileType.EMPTY, dtype=TileType
        )
        self.sprite_list = arcade.SpriteList()
        self._sprites: Dict[Tuple[int, int], arcade.Sprite] = {}

        for r in range(self.rows):
            for c in range(self.cols):
                sprite = arcade.Sprite()
                self._apply_type(sprite, self.grid[r, c])
                sprite.center_x = c * TILE_SIZE + TILE_SIZE / 2
                sprite.center_y = r * TILE_SIZE + TILE_SIZE / 2
                self.sprite_list.append(sprite)
                self._sprites[(r, c)] = sprite

        self.grid.subscribe(self._on_mutation)

    def _apply_type(self, sprite: arcade.Sprite, tile_type: TileType) -> None:
        if tile_type is TileType.EMPTY:
            sprite.visible = False
            return
        sprite.texture = _TEXTURE_BY_TYPE[tile_type]
        sprite.visible = True

    def _on_mutation(self, event: MutationEvent[TileType]) -> None:
        self._apply_type(self._sprites[(event.row, event.col)], event.new)

    def draw(self) -> None:
        self.sprite_list.draw()


class PlayerSprite(arcade.Sprite):
    FRAME_W = 16
    FRAME_H = 32
    IDLE_COUNT = 3
    RUN_COUNT = 8
    IDLE_FRAME_TIME = 0.75  # seconds per idle frame
    RUN_FRAME_TIME = 0.2   # seconds per run frame


    def __init__(self, sheet_path, scale=1.0):
        total = self.IDLE_COUNT + self.RUN_COUNT
        sheet = arcade.load_spritesheet(sheet_path)
        frames = sheet.get_texture_grid(
            size=(self.FRAME_W, self.FRAME_H),
            columns=total,
            count=total,
        )

        idle_right = frames[:self.IDLE_COUNT]
        run_right = frames[self.IDLE_COUNT:]

        # Sheet is drawn facing right; mirror once up front, not per frame.
        self._idle = {
            True: idle_right,
            False: [t.flip_left_right() for t in idle_right],
        }
        self._run = {
            True: run_right,
            False: [t.flip_left_right() for t in run_right],
        }

        super().__init__(idle_right[0], scale=scale)

        self.facing_right = True
        self._moving = False
        self._anim_time = 0.0

        self.vel_y = 0.0
        self.on_ground = False

    def update_animation(self, delta_time: float = 1 / 60):
        if self.change_x > 0:
            self.facing_right = True
        elif self.change_x < 0:
            self.facing_right = False

        moving = self.change_x != 0 and self.on_ground  # airborne -> idle frames
        if moving != self._moving:
            self._moving = moving
            self._anim_time = 0.0  # restart cycle on state change
        self._anim_time += delta_time

        if moving:
            frames, frame_time = self._run[self.facing_right], self.RUN_FRAME_TIME
        else:
            frames, frame_time = self._idle[self.facing_right], self.IDLE_FRAME_TIME

        self.texture = frames[int(self._anim_time / frame_time) % len(frames)]

class LanternLighting:
    LIGHT_COLOR = (0x59 / 255, 0x94 / 255, 0x3B / 255)  # #59943b
    RADIUS = 800.0     # light reaches nothing beyond this distance (px)
    INTENSITY = 3
    HEIGHT = 100.0     # how far the lantern sits "in front of" the screen; lower = more side-on
    AMBIENT = 0.7      # player brightness with no light

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

    FRAGMENT = """
    #version 330
    uniform sampler2D u_scene;
    uniform vec2 u_resolution;
    uniform vec2 u_light_pos;
    uniform vec3 u_light_color;
    uniform vec2 u_center;
    uniform vec2 u_half_size;
    uniform float u_radius;
    uniform float u_intensity;
    uniform float u_height;
    uniform float u_ambient;
    in vec2 uv;
    out vec4 frag_color;

    void main() {
        vec4 base = texture(u_scene, uv);
        if (base.a < 0.01) {
            frag_color = vec4(0.0);
            return;
        }

        vec2 frag = uv * u_resolution;

        // Fake normal: treat the sprite as an ellipsoid bulging toward the viewer.
        vec2 rel = (frag - u_center) / u_half_size;
        float nz = sqrt(max(0.0, 1.0 - dot(rel, rel)));
        vec3 n = normalize(vec3(rel, max(nz, 0.2)));

        vec3 to_light = vec3(u_light_pos - frag, u_height);
        vec3 L = normalize(to_light);
        float dist = length(to_light.xy);

        float atten = pow(clamp(1.0 - dist / u_radius, 0.0, 1.0), 2.0);
        float diffuse = max(dot(n, L), 0.0);

        vec3 lit = base.rgb * u_ambient
                 + base.rgb * u_light_color * diffuse * atten * u_intensity;
        frag_color = vec4(lit, base.a);
    }
    """

    def __init__(self, window):
        ctx = window.ctx
        self._window = window
        self._tex = ctx.texture(window.get_framebuffer_size(), components=4)
        self._tex.filter = ctx.NEAREST, ctx.NEAREST
        self._fbo = ctx.framebuffer(color_attachments=[self._tex])
        self._quad = geometry.quad_2d_fs()
        self._program = ctx.program(
            vertex_shader=self.VERTEX, fragment_shader=self.FRAGMENT
        )

    def draw(self, player_list, player, lantern_pos):
        with self._fbo.activate():
            self._fbo.clear(color=(0, 0, 0, 0))
            player_list.draw(filter=GL_NEAREST)

        self._tex.use(0)
        p = self._program
        p["u_scene"] = 0
        p["u_resolution"] = self._window.get_size()
        p["u_light_pos"] = lantern_pos
        p["u_light_color"] = self.LIGHT_COLOR
        p["u_center"] = player.position
        p["u_half_size"] = (player.width / 2, player.height / 2)
        p["u_radius"] = self.RADIUS
        p["u_intensity"] = self.INTENSITY
        p["u_height"] = self.HEIGHT
        p["u_ambient"] = self.AMBIENT
        self._quad.render(p)

class GameView(arcade.Window):
    SPAWN_DELAY = 0.25
    MAX_SPAWNS_PER_HOLD = 2
    MAX_REACH = 2
    MUTABLE = (TileType.MUTABLE_PERMANENT, TileType.MUTABLE_DECAY)
    GRAVITY = 0.25  # px/frame²
    JUMP_SPEED = 5.0  # px/frame (about 3 tiles of height)
    MAX_FALL_SPEED = 8.0
    EPS = 1e-3  # guards against float error at tile edges

    """
    Main application class.
    """

    def __init__(self):

        # Call the parent class to set up the window
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
        #self.set_draw_rate(2)

        self.background_color = arcade.csscolor.BLACK

        self.grid_renderer = GridRenderer()

        self.player = PlayerSprite(CHAR_SPRITE_PATH, scale=CHARACTER_SCALE)
        self.player_list = None
        self.player_sprite = None

        self.camera = arcade.Camera2D()
        self.camera.zoom = CAMERA_ZOOM

        #self.lighting = LanternLighting(self)
        self.space_held = False
        self.spawn_timer = 0.0
        self.spawned_this_hold = 0


    def setup(self):
        """Set up the game here. Call this function to restart the game."""
        self.player.center_x = SCREEN_WIDTH / 2
        self.player.center_y = (1 + 1) * TILE_SIZE + self.player.height / 2
        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player)
        #self.lantern_pos = (self.player.center_x + 400, self.player.center_y)

        load_ascii("./src/clavicula/maps/map-default.txt", self.grid_renderer.grid)

    def _cancel_hold(self):
        self.space_held = False
        self.spawn_timer = 0.0
        self.spawned_this_hold = 0

    def _spawn_target(self):
        """Cell the next tile would go in, or None if it can't be placed."""
        p = self.player
        g = self.grid_renderer

        foot_row = int((p.center_y - p.height / 2 + self.EPS) // TILE_SIZE)
        if p.facing_right:
            col = int((p.center_x + p.width / 2 - 1e-6) // TILE_SIZE) + 1
        else:
            col = int((p.center_x - p.width / 2) // TILE_SIZE) - 1

        if not 0 <= col < g.cols:
            return None

        # Climb the existing stack of decay tiles in this column.
        row = foot_row
        while row < g.rows and g.grid[row, col] is TileType.MUTABLE_DECAY:
            row += 1

        if row - foot_row >= self.MAX_REACH:  # out of reach: stack is already as high as we can place
            return None
        if not 1 <= row < g.rows:
            return None
        if g.grid[row, col] is not TileType.EMPTY:
            return None
        if g.grid[row - 1, col] not in self.MUTABLE:
            return None
        return row, col

    def maybe_spawn_tiles(self, delta_time):
        # Moving cancels the hold; press space again to restart.
        if self.player.change_x != 0:
            self._cancel_hold()
            return
        if not self.space_held or self.spawned_this_hold >= self.MAX_SPAWNS_PER_HOLD:
            self.spawn_timer = 0.0
            return

        target = self._spawn_target()
        if target is None:
            self.spawn_timer = 0.0  # pause only counts while placement is valid
            return

        self.spawn_timer += delta_time
        if self.spawn_timer >= self.SPAWN_DELAY:
            row, col = target
            self.grid_renderer.grid[row, col] = TileType.MUTABLE_DECAY
            self.spawned_this_hold += 1
            self.spawn_timer = 0.0  # next tile needs its own 1s pause

    def _player_columns(self):
        p = self.player
        left = int((p.center_x - p.width / 2) // TILE_SIZE)
        right = int((p.center_x + p.width / 2 - 1e-6) // TILE_SIZE)
        return range(left, right + 1)

    def _is_solid(self, row, col):
        g = self.grid_renderer
        if col < 0 or col >= g.cols:
            return True  # map edges are walls
        if row >= g.rows:
            return False
        if row < 0:
            return True  # bottom of the world is a floor
        return g.grid[row, col] is not TileType.EMPTY

    def _any_solid(self, row):
        return any(self._is_solid(row, c) for c in self._player_columns())

    def move_vertically(self):
        p = self.player
        p.vel_y = max(p.vel_y - self.GRAVITY, -self.MAX_FALL_SPEED)
        half = p.height / 2
        new_y = p.center_y + p.vel_y
        p.on_ground = False

        if p.vel_y <= 0:
            # Falling (or resting): find the highest floor between old and new feet.
            old_feet, new_feet = p.center_y - half, new_y - half
            top_row = math.floor((old_feet + self.EPS) / TILE_SIZE) - 1
            low_row = math.ceil(new_feet / TILE_SIZE) - 1
            for row in range(top_row, low_row - 1, -1):
                if self._any_solid(row):
                    p.center_y = (row + 1) * TILE_SIZE + half  # feet on the tile's top edge
                    p.vel_y = 0.0
                    p.on_ground = True
                    return
        else:
            # Rising: stop at the lowest ceiling between old and new head.
            old_head, new_head = p.center_y + half, new_y + half
            low_row = math.ceil((old_head - self.EPS) / TILE_SIZE)
            top_row = math.floor(new_head / TILE_SIZE)
            for row in range(low_row, top_row + 1):
                if self._any_solid(row):
                    p.center_y = row * TILE_SIZE - half  # head against the tile's underside
                    p.vel_y = 0.0
                    return

        p.center_y = new_y

    def resolve_horizontal(self):
        p = self.player
        if p.change_x == 0:
            return
        half_w, half_h = p.width / 2, p.height / 2

        # Rows the body covers (EPS keeps the floor under the feet out of the check).
        bottom = math.floor((p.center_y - half_h + self.EPS) / TILE_SIZE)
        top = math.floor((p.center_y + half_h - self.EPS) / TILE_SIZE)
        rows = range(bottom, top + 1)

        if p.change_x > 0:
            col = math.floor((p.center_x + half_w - 1e-6) / TILE_SIZE)
            if any(self._is_solid(r, col) for r in rows):
                p.center_x = col * TILE_SIZE - half_w  # flush with the tile's left side
        else:
            col = math.floor((p.center_x - half_w) / TILE_SIZE)
            if any(self._is_solid(r, col) for r in rows):
                p.center_x = (col + 1) * TILE_SIZE + half_w  # flush with the tile's right side

    def on_key_press(self, key, modifiers):
        if key == arcade.key.LEFT:
            self.player.change_x = -2
        elif key == arcade.key.RIGHT:
            self.player.change_x = 2
        elif key == arcade.key.SPACE:
            self.space_held = True
        elif key == arcade.key.UP:
            if self.player.on_ground:
                self.player.vel_y = self.JUMP_SPEED
                self.player.on_ground = False

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.LEFT, arcade.key.RIGHT):
            self.player.change_x = 0
        elif key == arcade.key.SPACE:
            self._cancel_hold()# whole native pixels avoid shimmer

    def update_camera(self):
        g = self.grid_renderer
        world_w, world_h = g.cols * TILE_SIZE, g.rows * TILE_SIZE
        half_w = self.width / CAMERA_ZOOM / 2
        half_h = self.height / CAMERA_ZOOM / 2
        x = min(max(self.player.center_x, half_w), world_w - half_w)
        y = min(max(self.player.center_y, half_h), world_h - half_h)
        self.camera.position = (round(x), round(y))

    def on_update(self, delta_time):
        self.player_list.update()  # applies change_x
        self.resolve_horizontal()
        self.move_vertically()
        self.player_list.update_animation(delta_time)
        self.maybe_spawn_tiles(delta_time)
        self.update_camera()

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.grid_renderer.draw()
        self.player_list.draw(filter=GL_NEAREST)


def main():
    """Main function"""
    window = GameView()
    window.setup()
    arcade.run()
