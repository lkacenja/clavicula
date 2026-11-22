import arcade


class PlayerSprite(arcade.Sprite):
    FRAME_W = 16
    FRAME_H = 32
    IDLE_COUNT = 3
    RUN_COUNT = 8
    IDLE_FRAME_TIME = 0.75  # seconds per idle frame
    RUN_FRAME_TIME = 0.2  # seconds per run frame

    def __init__(self, sheet_path, scale=1.0):
        total = self.IDLE_COUNT + self.RUN_COUNT
        sheet = arcade.load_spritesheet(sheet_path)
        frames = sheet.get_texture_grid(
            size=(self.FRAME_W, self.FRAME_H),
            columns=total,
            count=total,
        )

        idle_right = frames[: self.IDLE_COUNT]
        run_right = frames[self.IDLE_COUNT :]

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
