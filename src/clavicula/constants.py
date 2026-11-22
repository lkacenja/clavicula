from pathlib import Path
from typing import Final

# Paths (relative to the package, not the working directory)
PACKAGE_DIR: Final = Path(__file__).parent
ASSETS_DIR: Final = PACKAGE_DIR / "assets"
MAPS_DIR: Final = PACKAGE_DIR / "maps"
TILESET_PATH: Final = ASSETS_DIR / "tiles-animated.png"
CHAR_SPRITE_PATH: Final = ASSETS_DIR / "cla-char-sized.png"

# Display
WINDOW_WIDTH: Final = 1280
WINDOW_HEIGHT: Final = 720
WINDOW_TITLE: Final = "Clavicula"
TILE_SIZE: Final = 16
TILESET_COLUMNS: Final = 5
CAMERA_ZOOM: Final = 2
CHARACTER_SCALE = 1

# Tiling
SHEET_COLS = 19
FIRST_ANIM_CELL = 4
ANIM_COUNT = 3
ANIM_FRAMES = 5

# Physics (native px, per frame)
GRAVITY: Final = 0.25
JUMP_SPEED: Final = 5.0
MAX_FALL_SPEED: Final = 8.0
EPS: Final = 1e-3

# Tile spawning
SPAWN_DELAY: Final = 0.5
MAX_SPAWNS_PER_HOLD: Final = 2
MAX_REACH: Final = 2

PARTICLE_SIZE = 1
PARTICLE_ZONE = 1 / 3
PARTICLE_LIFE = 1.2          # seconds from birth to fully faded
PARTICLE_RATE = 30           # spores born per second while charging
PARTICLE_FALL = (4, 9)       # native px a spore settles downward over its life (min, max)
PARTICLE_DRIFT = 6           # max native px sideways, pushed outward from the tile centre
PARTICLE_OPACITY = 0.7       # peak opacity
PARTICLE_COLOR = (0x8C / 255, 0x97 / 255, 0x7C / 255)   # #8c977c, muted grey-green