import logging
from datetime import datetime
from collections import deque
from typing import Union
from dataclasses import dataclass, field

from discord import TextChannel, Member, User, VoiceChannel

import config.logger


@dataclass
class Audio:
    author: Union[Member, User]
    voice_channel: VoiceChannel
    text_channel: TextChannel
    audio_url: str
    webpage_url: str
    title: str
    length: float
    thumbnail: str
    start_time: datetime = field(init=False)
    end_time: datetime = field(init=False)

    def __str__(self) -> str:
        return self.title


class AudioQueue:
    def __init__(self, max_queue_size: int = 10000, max_previous_queue_size: int = 100):
        self.queue = deque()
        self.previous_queue = deque()
        self.current_audio = None
        self.max_queue_size = max_queue_size
        self.max_previous_queue_size = max_previous_queue_size

    async def append(self, audio: Audio) -> None:
        await self._add_to_queue(audio=audio, direction='right')

    async def append_left(self, audio: Audio) -> None:
        await self._add_to_queue(audio=audio, direction='left')

    def get_current_audio(self) -> Audio:
        return self.current_audio

    async def get_next_audio(self) -> Union[Audio, None]:
        next_audio = None
        if len(self.queue) > 0:
            if self.current_audio:
                self._add_to_previous_queue(audio=self.current_audio)
            next_audio = self.queue.popleft()
            self.current_audio = next_audio
            logging.info('Retrieved next song: %s', next_audio)
        else:
            if self.current_audio:
                self._add_to_previous_queue(audio=self.current_audio)
            self.current_audio = None
            logging.warning('Unable to get next song, queue is empty')
        return next_audio

    def _add_to_previous_queue(self, audio: Audio) -> None:
        if len(self.previous_queue) > self.max_previous_queue_size:
            self.previous_queue.popleft()
            self.previous_queue.append(audio)
        else:
            self.previous_queue.append(audio)

    async def get_previous_audio(self) -> Union[Audio, None]:
        previous_audio = None
        if len(self.previous_queue) > 0:
            if self.current_audio:
                self.queue.appendleft(self.current_audio)
            previous_audio = self.previous_queue.pop()
            self.current_audio = previous_audio
            logging.info('Retrieved previous audio: %s', previous_audio)
        else:
            logging.error('Unable to get previous audio, previous queue is empty')
        return previous_audio

    async def restart_queue(self) -> None:
        await self.append_left(self.current_audio)
        self.current_audio = None
        self.queue = self.previous_queue + self.queue
        self.previous_queue = deque()

    async def _add_to_queue(self, audio: Audio, direction: str = 'right'):
        if isinstance(audio, Audio):
            if self._is_below_max_queue_size():
                if direction == 'right':
                    self.queue.append(audio)
                elif direction == 'left':
                    self.queue.appendleft(audio)
                else:
                    self.queue.append(audio)
                    logging.error('Unknown direction \'direction\', appending to \'right\'')
                logging.info('Audio added to queue: %s', audio)
            else:
                logging.error('Unable to add audio, queue size greater than %s', self.max_queue_size)
        else:
            logging.error('Unable to add audio: Not an Audio object')

    def _is_below_max_queue_size(self) -> bool:
        return len(self.queue) < self.max_queue_size

    def reset_queue(self) -> None:
        self.current_audio = None
        self.clear_next_queue()
        self.clear_previous_queue()

    def clear_next_queue(self) -> None:
        self.queue = deque()

    def clear_previous_queue(self) -> None:
        self.previous_queue = deque()

    async def get_queue_as_str(self, amount: int = 5) -> Union[str, None]:
        next_audio = ''
        for idx in range(min(amount, len(self.queue))):
            next_audio += f'{idx+1}. {self.queue[idx]}\n'
        return None if next_audio == '' else next_audio

    async def get_previous_queue_as_str(self, amount: int = 3) -> Union[str, None]:
        previous_audio = ''
        for idx in range(min(amount, len(self.previous_queue))):
            previous_audio += f'{idx+1}. {self.previous_queue[-idx-1]}\n'
        return None if previous_audio == '' else previous_audio

    def get_queue_length(self) -> int:
        return len(self.queue)

    def get_previous_queue_length(self) -> int:
        return len(self.previous_queue)

    def __str__(self) -> str:
        next_audio = [f'{idx+1}. {x}' for idx, x in enumerate(self.queue)]
        next_audio = '\n'.join(next_audio)

        previous_audio = [f'{idx+1}. {x}' for idx, x in enumerate(self.previous_queue)]
        previous_audio = '\n'.join(previous_audio)

        songs = f'Current audio: {self.current_audio}\nNext audio: {next_audio}\nPrevious audio: {previous_audio}'
        return songs
