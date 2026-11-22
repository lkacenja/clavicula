"""
Platformer Game

python -m arcade.examples.platform_tutorial.01_open_window
"""

import math
import random

import arcade
from arcade.future.light.light_demo_perf import SCREEN_WIDTH

from pyglet.gl import GL_NEAREST

from clavicula.data.grid import TileType
from clavicula.data.ascii_loader import load_ascii
from clavicula.sprites.player import PlayerSprite
from clavicula.util.grid_renderer import GridRenderer, CHARGE_ANIMS
from clavicula.shaders.charge_particles import ChargeParticles
from clavicula.constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    CHAR_SPRITE_PATH,
    CHARACTER_SCALE,
    CAMERA_ZOOM,
    TILE_SIZE,
    SPAWN_DELAY,
    MAX_REACH,
    MAX_SPAWNS_PER_HOLD,
    EPS
)

class GameView(arcade.Window):
    SPAWN_DELAY = 0.25
    MAX_SPAWNS_PER_HOLD = 2
    MAX_REACH = 2
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
        # self.set_draw_rate(2)

        self.background_color = arcade.csscolor.BLACK

        self.grid_renderer = GridRenderer()

        self.player = PlayerSprite(CHAR_SPRITE_PATH, scale=CHARACTER_SCALE)
        self.player_list = None
        self.player_sprite = None

        self.camera = arcade.Camera2D()
        self.camera.zoom = CAMERA_ZOOM

        # self.shaders = LanternLighting(self)
        self.space_held = False
        self.spawn_timer = 0.0
        self.spawned_this_hold = 0
        self.charge_variant = None

        self.charge_sprite = arcade.Sprite(CHARGE_ANIMS[0][0])
        self.charge_sprite.visible = False
        self.charge_list = arcade.SpriteList()
        self.charge_list.append(self.charge_sprite)

        self.particles = ChargeParticles(self)
        self.charge_emitter = None

    def setup(self):
        """Set up the game here. Call this function to restart the game."""
        self.player.center_x = SCREEN_WIDTH / 2
        self.player.center_y = (1 + 1) * TILE_SIZE + self.player.height / 2
        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player)
        # self.lantern_pos = (self.player.center_x + 400, self.player.center_y)

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
        while row < g.rows and g.grid[row, col] is TileType.MUTABLE:
            row += 1

        if (
            row - foot_row >= self.MAX_REACH
        ):  # out of reach: stack is already as high as we can place
            return None
        if not 1 <= row < g.rows:
            return None
        if g.grid[row, col] is not TileType.EMPTY:
            return None
        if g.grid[row - 1, col] is not TileType.MUTABLE:
            return None
        return row, col

    def _spawn_target(self):
        p = self.player
        g = self.grid_renderer

        foot_row = int((p.center_y - p.height / 2 + EPS) // TILE_SIZE)
        if p.facing_right:
            col = int((p.center_x + p.width / 2 - 1e-6) // TILE_SIZE) + 1
        else:
            col = int((p.center_x - p.width / 2) // TILE_SIZE) - 1

        if not 0 <= col < g.cols:
            return None

        row = foot_row
        while row < g.rows and g.grid[row, col] is TileType.MUTABLE:
            row += 1  # climb the existing stack

        if row - foot_row >= MAX_REACH:  # out of reach
            return None
        if not 1 <= row < g.rows:
            return None
        if g.grid[row, col] is not TileType.EMPTY:
            return None
        if g.grid[row - 1, col] is not TileType.MUTABLE:  # needs mutable support
            return None
        return row, col

    def _stop_charge(self, keep_emitter=False):
        self.spawn_timer = 0.0
        self.charge_variant = None
        self.charge_sprite.visible = False
        if not keep_emitter and self.charge_emitter is not None:
            self.particles.end(self.charge_emitter)
            self.charge_emitter = None

    def _cancel_hold(self):
        self.space_held = False
        self.spawned_this_hold = 0
        self._stop_charge()

    def maybe_spawn_tiles(self, delta_time):
        if self.player.change_x != 0:  # moving cancels the hold
            self._cancel_hold()
            return
        if not self.space_held or self.spawned_this_hold >= MAX_SPAWNS_PER_HOLD:
            self._stop_charge()
            return

        target = self._spawn_target()
        if target is None:
            self._stop_charge()
            return

        row, col = target
        if self.charge_variant is None:
            self.charge_variant = random.randrange(len(CHARGE_ANIMS))
        if self.charge_emitter is None:  # first tile of the hold; the second reuses it
            self.charge_emitter = self.particles.begin(target, random.random() * 100.0)
        self.spawn_timer += delta_time

        if self.spawn_timer >= SPAWN_DELAY:
            self.grid_renderer.set_mutable(row, col, self.charge_variant)
            self.spawned_this_hold += 1
            self._stop_charge(keep_emitter=True)  # the second tile keeps emitting from the first
            return

        frames = CHARGE_ANIMS[self.charge_variant]  # frame from timer progress
        s = self.charge_sprite
        s.texture = frames[int(self.spawn_timer / SPAWN_DELAY * len(frames))]
        s.position = (col * TILE_SIZE + TILE_SIZE / 2, row * TILE_SIZE + TILE_SIZE / 2)
        s.visible = True

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
                    p.center_y = (
                        row + 1
                    ) * TILE_SIZE + half  # feet on the tile's top edge
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
                    p.center_y = (
                        row * TILE_SIZE - half
                    )  # head against the tile's underside
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
                p.center_x = (
                    col + 1
                ) * TILE_SIZE + half_w  # flush with the tile's right side

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
            self._cancel_hold()  # whole native pixels avoid shimmer

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
        self.particles.update(delta_time)
        self.update_camera()

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.grid_renderer.draw()
        self.charge_list.draw(filter=GL_NEAREST)
        self.particles.draw(self.camera)
        self.player_list.draw(filter=GL_NEAREST)



def main():
    """Main function"""
    window = GameView()
    window.setup()
    arcade.run()
