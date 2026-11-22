import math
import random
from typing import Dict, Tuple

import arcade
from pyglet.gl import GL_NEAREST

from clavicula.constants import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    TILE_SIZE,
    TILESET_PATH,
    SHEET_COLS,
    FIRST_ANIM_CELL,
    ANIM_FRAMES,
    ANIM_COUNT,
)
from clavicula.data.grid import TypedGrid, TileType, MutationEvent

TILE_INDEX = {TileType.IMMUTABLE: 0}      # EMPTY is never drawn

_sheet = arcade.SpriteSheet(TILESET_PATH)

_textures = _sheet.get_texture_grid(
    size=(TILE_SIZE, TILE_SIZE), columns=SHEET_COLS, count=SHEET_COLS,
)
_STATIC_TEXTURES = {t: _textures[i] for t, i in TILE_INDEX.items()}

CHARGE_ANIMS = [
    _textures[FIRST_ANIM_CELL + ANIM_FRAMES * k : FIRST_ANIM_CELL + ANIM_FRAMES * (k + 1)]
    for k in range(ANIM_COUNT)
]
MUTABLE_TEXTURES = [anim[-1] for anim in CHARGE_ANIMS]


class GridRenderer:
    def __init__(self):
        self.rows = math.ceil(WINDOW_HEIGHT / TILE_SIZE)
        self.cols = math.ceil(WINDOW_WIDTH / TILE_SIZE)
        self.grid: TypedGrid[TileType] = TypedGrid(
            self.rows, self.cols, default=TileType.EMPTY, dtype=TileType
        )
        self.sprite_list = arcade.SpriteList()
        self._sprites: Dict[Tuple[int, int], arcade.Sprite] = {}
        self.variants: Dict[Tuple[int, int], int] = {}

        for r in range(self.rows):
            for c in range(self.cols):
                sprite = arcade.Sprite()
                self._apply_type(sprite, self.grid[r, c])
                sprite.center_x = c * TILE_SIZE + TILE_SIZE / 2
                sprite.center_y = r * TILE_SIZE + TILE_SIZE / 2
                self.sprite_list.append(sprite)
                self._sprites[(r, c)] = sprite

        self.grid.subscribe(self._on_mutation)

    def _apply_type(self, sprite, tile_type, variant=0):
        if tile_type is TileType.EMPTY:
            sprite.visible = False
            return
        if tile_type is TileType.MUTABLE:
            sprite.texture = MUTABLE_TEXTURES[variant]
        else:
            sprite.texture = _STATIC_TEXTURES[tile_type]
        sprite.visible = True

    def _on_mutation(self, event):
        key = (event.row, event.col)
        if event.new is TileType.MUTABLE:
            # Loader-placed tiles arrive with no variant yet; give them a random one.
            self.variants.setdefault(key, random.randrange(len(MUTABLE_TEXTURES)))
        else:
            self.variants.pop(key, None)  # removal still clears it
        self._apply_type(self._sprites[key], event.new, self.variants[key] if key in self.variants else 0)

    def set_mutable(self, row, col, variant):
        self.variants[(row, col)] = variant  # set first so _on_mutation sees it
        self.grid[row, col] = TileType.MUTABLE

    def draw(self) -> None:
        self.sprite_list.draw(filter=GL_NEAREST)
