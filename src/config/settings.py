from typing import Final


FFMPEG_OPTS: Final[dict] = {'before_options': ['-reconnect 1', '-reconnect_streamed 1', '-reconnect_delay_max 5'], # -ss [seconds] to skip
                            'options': ['-vn']}
DELETE_TIMER: Final[int] = 5
