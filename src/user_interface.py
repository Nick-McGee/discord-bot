import logging
from datetime import datetime
from typing import Callable, Union
from asyncio import sleep
from threading import Lock

from discord import Bot, TextChannel, Guild, Interaction, Embed, ButtonStyle
from discord.ui import Button, View
from discord.errors import NotFound
from discord.ext import tasks

from audio import AudioQueue
import config.logger


class UserInterface:
    def __init__(self,
                 change_audio_function: Callable,
                 queue: AudioQueue):
        self.change_audio_function = change_audio_function
        self.queue = queue
        self.current_ui = None
        self.lock = Lock()

    @tasks.loop(seconds=3)
    async def auto_refresh_ui_fast(self) -> None:
        self.auto_refresh_ui_slow.stop()
        await self.refresh_ui()

    @tasks.loop(minutes=1)
    async def auto_refresh_ui_slow(self) -> None:
        self.auto_refresh_ui_fast.stop()
        await self.refresh_ui()

    def start_auto_refresh_ui_fast(self) -> None:
        if not self.auto_refresh_ui_fast.is_running():
            try:
                self.auto_refresh_ui_fast.start()
            except RuntimeError as runtime_error:
                logging.debug('Auto refresh fast is already running: %s', runtime_error)

    def start_auto_refresh_ui_slow(self) -> None:
        if not self.auto_refresh_ui_slow.is_running():
            try:
                self.auto_refresh_ui_fast.start()
            except RuntimeError as runtime_error:
                logging.debug('Auto refresh slow is already running: %s', runtime_error)

    def stop_tasks(self) -> None:
        self.auto_refresh_ui_fast.stop()
        self.auto_refresh_ui_slow.stop()

    async def new_ui(self, text_channel: TextChannel) -> None:
        logging.info('Creating new UI')
        view = await self.get_view()
        embed = await self.get_embed()

        await self.acquire_lock()

        try:
            if self.current_ui:
                await self.current_ui.delete()
            self.current_ui = await text_channel.send(embed=embed, view=view)
        except NotFound as not_found:
            logging.error('UI not found: %s', not_found)
        finally:
            await self.release_lock()

    async def refresh_ui(self) -> None:
        logging.info('Refreshing UI')
        view = await self.get_view()
        embed = await self.get_embed()

        try:
            if self.current_ui is not None:
                await self.current_ui.edit(embed=embed, view=view)
        except NotFound as not_found:
            logging.error('UI not found: %s', not_found)

    async def delete_ui(self, bot: Bot, guild: Guild) -> None:
        await self.acquire_lock()

        try:
            message_list = []
            for text_channels in guild.text_channels:
                message_list.append(await text_channels.history(limit=100).flatten())

            for channel in message_list:
                for message in channel:
                    if message.author.id == bot.user.id:
                        await message.delete()

            self.current_ui = None

        except NotFound as not_found:
            logging.error('UI not found: %s', not_found)
        finally:
            await self.release_lock()

    async def acquire_lock(self) -> None:
        while not self.lock.acquire(blocking=False):
            await sleep(0.1)

    async def release_lock(self) -> None:
        try:
            self.lock.release()
        except RuntimeError as runtime_error:
            logging.debug('Queue lock is already released, %s', runtime_error)

    async def get_embed(self) -> Embed:
        if self.queue.get_current_audio() is None:
            embed = Embed(title='Not Playing')
        else:
            current_audio = self.queue.get_current_audio()
            embed = Embed(title=current_audio.title)

            try:
                time_left = self.calculate_time_left(end_time=current_audio.end_time)
                embed.add_field(name='Time Left', value=time_left, inline=False)
            except AttributeError as attribute_error:
                logging.error(attribute_error)

            embed.set_image(url=current_audio.thumbnail)
            if current_audio.author is not None:
                embed.set_footer(text=f'Requested by {current_audio.author.display_name}',
                                icon_url=current_audio.author.display_avatar)

        next_audio_string = await self._get_audio_queue_strings(queue_type='next', amount=5)
        if next_audio_string:
            embed.add_field(name='Next', value=next_audio_string, inline=False)

        previous_audio_string = await self._get_audio_queue_strings(queue_type='prev', amount=3)
        if previous_audio_string:
            embed.add_field(name='Previous', value=previous_audio_string, inline=False)

        return embed

    async def _get_audio_queue_strings(self, queue_type: str, amount: int = 5) -> Union[str, None]:
        if queue_type == 'next':
            audios = await self.queue.get_queue_as_str(amount=amount)
        elif queue_type == 'prev':
            audios = await self.queue.get_previous_queue_as_str(amount=amount)
        else:
            logging.error('Unknown queue type \'%s\', defaulting to \'next\'')
            audios = await self.queue.get_queue_as_str(amount=amount)

        if audios:
            if queue_type == 'next':
                amount_past_max = self.queue.get_queue_length() - amount
            elif queue_type == 'prev':
                amount_past_max = self.queue.get_previous_queue_length() - amount
            else:
                amount_past_max = self.queue.get_queue_length() - amount

            if amount_past_max > 0:
                audios += f'**+ {amount_past_max} more**'

        return audios

    async def get_view(self) -> View:
        if self.queue.get_previous_queue_length() > 0:
            previous_audio_button = Button(style=ButtonStyle.secondary, emoji='⏮')
        else:
            previous_audio_button = Button(disabled=True, style=ButtonStyle.secondary, emoji='⏮')
        previous_audio_button.callback = self.previous_audio_callback

        if self.queue.get_queue_length() > 0 or self.queue.get_current_audio():
            next_audio_button = Button(style=ButtonStyle.secondary, emoji='⏭')
        else:
            next_audio_button = Button(disabled=True, style=ButtonStyle.secondary, emoji='⏭')
        next_audio_button.callback = self.next_audio_callback

        view = View(previous_audio_button, next_audio_button)

        if self.queue.get_current_audio() is not None:
            go_to_youtube = Button(style=ButtonStyle.url, label='See on YouTube', url=self.queue.get_current_audio().webpage_url)
            view.add_item(go_to_youtube)

        return view

    async def previous_audio_callback(self, interaction: Interaction):
        logging.info('Previous audio button selected')
        if interaction.user.voice and interaction.user.voice.channel is not None:
            await self.change_audio_function(direction='prev')

    async def next_audio_callback(self, interaction: Interaction):
        logging.info('Next audio button selected: %s', interaction.user)
        if interaction.user.voice and interaction.user.voice.channel is not None:
            await self.change_audio_function(direction='next')

    @staticmethod
    def calculate_time_left(end_time: datetime) -> str:
        time_left = end_time - datetime.now()
        tot_sec = time_left.total_seconds()
        if tot_sec > 0:
            hours = int(tot_sec // 3600)
            minutes = int((tot_sec % 3600) // 60)
            secs = int((tot_sec % 3600) % 60)

            time_left = f'{hours:02}:{minutes:02}:{secs:02}'
        else:
            time_left = '00:00:00'

        return time_left
