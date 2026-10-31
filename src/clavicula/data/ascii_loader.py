from pathlib import Path
from clavicula.data.grid import TileType, TypedGrid

GLYPH_TO_TILE: dict[str, TileType] = {
    ".": TileType.EMPTY,
    "#": TileType.IMMUTABLE,          # solid wall, never changes
    "=": TileType.MUTABLE_PERMANENT,  # player-creatable, stays
    "~": TileType.MUTABLE_DECAY,      # player-creatable, decays
}

def load_ascii(path: str, grid: TypedGrid[TileType]) -> None:
    rows, cols = grid.shape
    lines = Path(path).read_text().splitlines()
    if len(lines) > rows:
        raise ValueError(f"{path}: {len(lines)} rows, grid holds {rows}")

    for r, line in enumerate(reversed(lines)):
        if len(line) > cols:
            raise ValueError(f"{path}: row is {len(line)} wide, grid holds {cols}")
        for c, ch in enumerate(line):
            try:
                grid[r, c] = GLYPH_TO_TILE[ch]
            except KeyError:
                raise ValueError(f"{path}: unknown glyph {ch!r} at line {len(lines) - r}, col {c + 1}")