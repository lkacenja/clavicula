import math
from typing import Dict, Tuple

import arcade

from clavicula.constants import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    TILE_SIZE,
    TILESET_PATH,
    TILESET_COLUMNS,
)
from clavicula.data.grid import TypedGrid, TileType, MutationEvent

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
