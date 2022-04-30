import logging

from discord import Bot, VoiceChannel
from discord.errors import ClientException

import config.logger


class Voice:
    def __init__(self, bot: Bot):
        self.client = None
        self.bot = bot

    async def check_voice(self, voice_channel: VoiceChannel):
        if self.client and self.client.is_connected():
            logging.debug('Remaining in current channel: %s', self.client.channel)
        else:
            await self.join_voice(voice_channel=voice_channel)

    async def join_voice(self, voice_channel: VoiceChannel) -> None:
        try:
            await voice_channel.connect()
            logging.info('Connected to new voice channel: %s', voice_channel)
        except ClientException:
            await self.client.move_to(voice_channel)
            logging.info('Moved to to new voice channel: %s', voice_channel)
        self.client = self.bot.voice_clients[0]

    async def reset_voice(self) -> None:
        await self.disconnect_voice()
        self.client = None

    async def disconnect_voice(self) -> None:
        try:
            await self.client.disconnect(force=True)
        except (AttributeError, TypeError) as missing_client:
            logging.warning('No voice client connected to stop: %s', missing_client)

    async def stop_voice(self) -> None:
        try:
            await self.client.stop()
        except (AttributeError, TypeError) as missing_client:
            logging.warning('No voice client connected to stop: %s', missing_client)

    def is_playing(self) -> bool:
        return self.client is not None and self.client.is_playing()
