import logging
from threading import Lock
from abc import ABC, abstractmethod

from discord import Bot, TextChannel, Guild, Embed
from discord.ui import View
from discord.errors import NotFound
from discord.ext import tasks

import config.logger


class UserInterface(ABC):
    def __init__(self):
        self.current_ui = None
        self.lock = Lock()

    @tasks.loop(seconds=2.5)
    async def _auto_refresh_ui(self) -> None:
        await self.refresh_ui()

    def start_auto_refresh(self) -> None:
        if not self._auto_refresh_ui.is_running():
            self._auto_refresh_ui.start()

    def stop_auto_refresh(self) -> None:
        self._auto_refresh_ui.stop()

    def restart_auto_refresh(self) -> None:
        self._auto_refresh_ui.restart()

    async def new_ui(self, text_channel: TextChannel) -> None:
        self.start_auto_refresh()
        if text_channel is None:
            logging.warning('Invalid text channel, attempting refresh')
            await self.refresh_ui()
            return

        logging.info('Creating new UI')
        self.lock.acquire(blocking=False)
        view = await self.get_view()
        embed = await self.get_embed()

        try:
            if self.current_ui:
                await self.current_ui.delete()
            self.current_ui = await text_channel.send(embed=embed, view=view)
        except NotFound as not_found:
            logging.error('UI not found: %s', not_found)
        finally:
            await self._release_lock()

    async def refresh_ui(self) -> None:
        logging.info('Refreshing UI')
        if not self.lock.acquire(blocking=False):
            logging.warning('UI locked, refreshing UI stopped')
            return

        view = await self.get_view()
        embed = await self.get_embed()

        try:
            if self.current_ui is not None:
                await self.current_ui.edit(embed=embed, view=view)
        except NotFound as not_found:
            logging.error('UI not found: %s', not_found)
        finally:
            await self._release_lock()

    async def delete_ui(self, bot: Bot, guild: Guild, ignore_msg_ids: set[int | None] | None = None) -> None:
        self.lock.acquire(blocking=False)
        self.stop_auto_refresh()

        try:
            channel_list = []
            for text_channels in guild.text_channels:
                channel_list.append(await text_channels.history(limit=100).flatten())

            for channel in channel_list:
                for message in channel:
                    if isinstance(ignore_msg_ids, set) and message.id in ignore_msg_ids:
                        pass
                    elif message.author.id == bot.user.id:
                        await message.delete()

            self.current_ui = None

        except NotFound as not_found:
            logging.error('UI not found: %s', not_found)
        finally:
            await self._release_lock()

    async def _release_lock(self) -> None:
        try:
            self.lock.release()
        except RuntimeError as runtime_error:
            logging.debug('Queue lock is already released, %s', runtime_error)

    @abstractmethod
    async def get_embed(self) -> Embed:
        pass

    @abstractmethod
    async def get_view(self) -> View:
        pass
