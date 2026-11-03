from pathlib import Path
from typing import Final

# Paths (relative to the package, not the working directory)
PACKAGE_DIR: Final = Path(__file__).parent
ASSETS_DIR: Final = PACKAGE_DIR / "assets"
MAPS_DIR: Final = PACKAGE_DIR / "maps"
TILESET_PATH: Final = ASSETS_DIR / "tiles.png"
CHAR_SPRITE_PATH: Final = ASSETS_DIR / "cla-char-sized.png"

# Display
WINDOW_WIDTH: Final = 1280
WINDOW_HEIGHT: Final = 720
WINDOW_TITLE: Final = "Clavicula"
TILE_SIZE: Final = 16
TILESET_COLUMNS: Final = 5
CAMERA_ZOOM: Final = 2
CHARACTER_SCALE = 1

# Physics (native px, per frame)
GRAVITY: Final = 0.25
JUMP_SPEED: Final = 5.0
MAX_FALL_SPEED: Final = 8.0
EPS: Final = 1e-3

# Tile spawning
SPAWN_DELAY: Final = 0.5
MAX_SPAWNS_PER_HOLD: Final = 2
MAX_REACH: Final = 2
