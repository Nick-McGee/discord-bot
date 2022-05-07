import logging
from typing import Callable
from asyncio import to_thread

from discord import Bot, VoiceChannel, FFmpegPCMAudio, PCMVolumeTransformer
from discord.errors import ClientException
from discord.opus import OpusNotLoaded
from audio import Audio

from async_event_handler import subscribe

import config.logger
from config.settings import FFMPEG_OPTS


class Voice:
    __slots__ = 'bot', 'after_function', 'client'

    def __init__(self,
                 bot: Bot,
                 after_function: Callable | None = None):
        self.bot = bot
        self.after_function = after_function
        self.client = None
        subscribe(event_type = 'new_audio', function = self.stream)
        subscribe(event_type = 'no_audio', function = self.disconnect_voice)

    async def join_voice(self, voice_channel: VoiceChannel) -> None:
        try:
            await voice_channel.connect()
            logging.debug('Connected to new voice channel: %s', voice_channel)
        except ClientException:
            await self.client.move_to(voice_channel)
            logging.debug('Moved to to new voice channel: %s', voice_channel)
        self.client = self.bot.voice_clients[0]

    async def check_voice(self, voice_channel: VoiceChannel):
        if self.client and self.client.is_connected():
            logging.debug('Remaining in current channel: %s', self.client.channel)
        else:
            await self.join_voice(voice_channel=voice_channel)

    async def stream(self, audio: Audio) -> None:
        await self.check_voice(voice_channel=audio.voice_channel)
        audio_source = PCMVolumeTransformer(FFmpegPCMAudio(source=audio.audio_url, **FFMPEG_OPTS), volume=0.1)
        if self.is_playing():
            self.client.source = audio_source
        else:
            try:
                await to_thread(self.client.play(source=audio_source, after=self.after))
            except (TypeError, AttributeError, ClientException, OpusNotLoaded) as error_msg:
                logging.error('Error playing audio: %s', error_msg)

    def after(self, e: Exception) -> Callable | None:
        if e:
            logging.error('Play error: %s', e)
        if self.after_function:
            self.after_function()

    async def disconnect_voice(self) -> None:
        try:
            await self.client.disconnect(force=True)
        except (AttributeError, TypeError) as missing_client:
            logging.warning('No voice client connected to stop: %s', missing_client)
        self.client = None

    def stop_voice(self) -> None:
        try:
            self.client.stop()
        except (AttributeError, TypeError) as missing_client:
            logging.warning('No voice client connected to stop: %s', missing_client)

    def is_playing(self) -> bool:
        return self.client is not None and self.client.is_playing()
