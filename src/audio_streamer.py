import logging
from typing import Union
from datetime import datetime, timedelta
from threading import Lock
from asyncio import sleep, get_event_loop

from discord import Bot, FFmpegPCMAudio, PCMVolumeTransformer, ApplicationContext, TextChannel, User, Member, VoiceChannel, Embed, Colour
from discord.ext import commands, tasks
from discord.commands import slash_command, Option
from discord.errors import ClientException
from discord.opus import OpusNotLoaded
from pytube import Playlist

from audio import Audio, AudioQueue
from voice import Voice
from user_interface import UserInterface
from youtube_client import get_audio, get_playlist
import config.logger
from config.settings import FFMPEG_OPTS, DELETE_TIMER
from config.auth import GUILD_ID


class AudioStreamer(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.queue = AudioQueue()
        self.voice = Voice(bot=bot)
        self.user_interface = UserInterface(change_audio_function = self.change_audio,
                                            queue = self.queue)
        self.lock = Lock()
        self.cancel_queue_playlist = False
        self.timeout_check = False

    @slash_command(name='play', description='Queue YouTube audio files via a search query or URL', guild_ids=[GUILD_ID])
    async def play_command(self, ctx: ApplicationContext, query: Option(str, 'Search or URL')) -> None:
        logging.info('Play command invoked')
        self.start_queue_ui_tasks()
        audio_title = await self.queue_audio(author=ctx.author,
                                             voice_channel=ctx.author.voice.channel,
                                             text_channel=ctx.channel,
                                             query=query)
        if audio_title:
            await ctx.respond(embed=Embed(title='Queued', description=f'**{audio_title}**', color=Colour.green()),
                              delete_after=DELETE_TIMER)
        else:
            await ctx.respond(embed=Embed(title='Error', description=f'Unable to queue **{query}**', color=Colour.red()),
                              delete_after=DELETE_TIMER)

    @slash_command(name='play_next', description='Queue up next YouTube audio files via a search query or URL', guild_ids=[GUILD_ID])
    async def play_next_command(self, ctx: ApplicationContext, query: Option(str, 'Search or URL')) -> None:
        logging.info('Play next command invoked')
        self.start_queue_ui_tasks()
        audio_title = await self.queue_audio(author=ctx.author,
                                             voice_channel=ctx.author.voice.channel,
                                             text_channel=ctx.channel,
                                             query=query,
                                             add_to_start=True)
        if audio_title:
            await ctx.respond(embed=Embed(title='Queued Next', description=f'**{audio_title}**', color=Colour.green()),
                              delete_after=DELETE_TIMER)
        else:
            await ctx.respond(embed=Embed(title='Error', description=f'Unable to queue next **{query}**', color=Colour.red()),
                              delete_after=DELETE_TIMER)

    @slash_command(name='playlist', description='Queue a series of audio files from a YouTube Playlist URL', guild_ids=[GUILD_ID])
    async def playlist_command(self, ctx: ApplicationContext, url: Option(str, 'A playlist URL')) -> None:
        logging.info('Playlist command invoked')
        self.start_queue_ui_tasks()
        playlist = get_playlist(playlist_url=url)
        try:
            if len(playlist) == 0:
                await ctx.respond(embed=Embed(title='Error', description=f'Unable to queue playlist **{url}**', color=Colour.red()),
                                  delete_after=DELETE_TIMER)
            else:
                await ctx.respond(embed=Embed(title='Queuing Playlist',
                                              description=playlist.title,
                                              color=Colour.green()),
                                  delete_after=DELETE_TIMER)

                await self.queue_playlist(author=ctx.author,
                                          voice_channel=ctx.author.voice.channel,
                                          text_channel=ctx.channel,
                                          playlist=playlist)
        except KeyError as key_error:
            logging.error('Key error queuing playlist: %s', key_error)
            await ctx.respond(embed=Embed(title='Error', description=f'Unable to queue playlist **{url}**', color=Colour.red()),
                              delete_after=DELETE_TIMER)

    @slash_command(name='restart_queue', description='Start playing from the beginning of the previous queue', guild_ids=[GUILD_ID])
    async def restart_queue(self, ctx: ApplicationContext) -> None:
        logging.info('Restart queue command invoked')
        await self.acquire_lock()
        await self.voice.stop_voice()
        self.start_queue_ui_tasks()
        await self.queue.restart_queue()
        await self.release_lock()

        await ctx.respond(embed=Embed(title='Restarted Queue', color=Colour.green()),
                          delete_after=DELETE_TIMER)

    @slash_command(name='clear_queue', description='Clear the up next queue', guild_ids=[GUILD_ID])
    async def clear_up_next_command(self, ctx: ApplicationContext) -> None:
        logging.info('Clear command invoked')
        self.cancel_queue_playlist = True
        self.queue.clear_next_queue()
        await ctx.respond(embed=Embed(title='Cleared Up Next Queue', color=Colour.green()),
                          delete_after=DELETE_TIMER)

    @slash_command(name='clear_previous_queue', description='Clear the previous queue', guild_ids=[GUILD_ID])
    async def clear_previous_command(self, ctx: ApplicationContext) -> None:
        logging.info('Clear command invoked')
        self.queue.clear_previous_queue()
        await ctx.respond(embed=Embed(title='Cleared Previous Queue', color=Colour.green()),
                          delete_after=DELETE_TIMER)

    @slash_command(name='remove', description='Skips and removes the currently playing song from the queue', guild_ids=[GUILD_ID])
    async def remove_command(self, ctx: ApplicationContext) -> None:
        logging.info('Remove from queue command invoked')
        await self.acquire_lock()

        if self.queue.get_current_audio():
            song_title = self.queue.get_current_audio().title
            self.queue.current_audio = None
            await self.voice.stop_voice()
            await ctx.respond(embed=Embed(title='Remove from Queue', description=f'Removed **{song_title}**', color=Colour.green()),
                              delete_after=DELETE_TIMER)
        else:
            await ctx.respond(embed=Embed(title='Unable to Remove from Queue', description='Unable to find current audio to remove', color=Colour.green()),
                              delete_after=DELETE_TIMER)

        await self.release_lock()

    @slash_command(name='reset', description='Reset the voice client, queue, and user interface', guild_ids=[GUILD_ID])
    async def reset_command(self, ctx: ApplicationContext) -> None:
        logging.info('Reset command invoked')
        await self.voice.reset_voice()
        await self.reset_queue()
        await self.user_interface.delete_ui(bot=self.bot, guild=ctx.guild)
        self.stop_tasks()
        await self.release_lock()

        await ctx.respond(embed=Embed(title='Reset Bot',
                                      description=f'**{self.bot.user.display_name}** has been reset',
                                      color=Colour.green()),
                          delete_after=DELETE_TIMER)

    @slash_command(name='reconnect_bot', description='Reconnect the bot to your voice channel and text channel', guild_ids=[GUILD_ID])
    async def reconnect_bot(self, ctx: ApplicationContext) -> None:
        logging.info('Reconnect command invoked')
        try:
            await self.voice.join_voice(voice_channel=ctx.author.voice.channel)
            await self.user_interface.new_ui(text_channel=ctx.channel)
            await ctx.respond(embed=Embed(title='Reconnected',
                                          description=f'**{self.bot.user.display_name}** connected to voice channel **{ctx.author.voice.channel}** and text channel **{ctx.channel}**',
                                          color=Colour.green()),
                              delete_after=DELETE_TIMER)
            logging.info('Bot reconnected')
        except AttributeError as attribute_error:
            logging.error('Unable to connect bot to voice: %s', attribute_error)
            await ctx.respond(embed=Embed(title='Unable to Connect', description=f'Error connecting **{self.bot.user.display_name}** to voice', color=Colour.red()),
                              delete_after=DELETE_TIMER)

    @tasks.loop(seconds=0.5)
    async def check_queue(self):
        if not self.voice.is_playing() and not self.lock.locked() and self.queue.get_queue_length() > 0:
            await self.change_audio(direction='next')

    @tasks.loop(minutes=15)
    async def timeout(self) -> None:
        if not self.voice.is_playing():
            if self.timeout_check is True:
                self.stop_tasks()
                self.user_interface.start_auto_refresh_ui_slow()
                await self.voice.reset_voice()
            else:
                self.timeout_check = True
        else:
            self.user_interface.auto_refresh_ui_slow.stop()
            self.timeout_check = False

    @commands.Cog.listener()
    async def on_ready(self):
        self.timeout.start()
        await self.bot.wait_until_ready()
        guild = self.bot.guilds[0]
        await self.user_interface.delete_ui(bot=self.bot, guild=guild)

    @play_command.before_invoke
    @play_next_command.before_invoke
    @playlist_command.before_invoke
    @restart_queue.before_invoke
    @clear_up_next_command.before_invoke
    @clear_previous_command.before_invoke
    @remove_command.before_invoke
    @reset_command.before_invoke
    @reconnect_bot.before_invoke
    async def ensure_voice(self, ctx: ApplicationContext) -> None:
        await ctx.defer()
        if ctx.author and ctx.author.voice is None:
            await ctx.respond(embed=Embed(title='Error', description='You are not connected to a voice channel', color=Colour.red()),
                              delete_after=DELETE_TIMER)

    async def queue_audio(self,
                          query: str,
                          author: Union[User, Member],
                          voice_channel: VoiceChannel,
                          text_channel: TextChannel,
                          add_to_start: bool = False) -> Union[str, None]:
        logging.info('Queuing %s', query)
        loop = get_event_loop()
        audio = await loop.run_in_executor(None, get_audio, query, author, voice_channel, text_channel)
        audio_title = None

        if audio:
            logging.info('Queued %s %s', audio.title, audio.audio_url)
            if add_to_start:
                await self.queue.append_left(audio=audio)
            else:
                await self.queue.append(audio=audio)
            await self.user_interface.refresh_ui()
            audio_title = audio.title
        else:
            logging.error('Unable to queue audio %s', query)

        return audio_title

    async def queue_playlist(self,
                             author: Union[User, Member],
                             voice_channel: VoiceChannel,
                             text_channel: TextChannel,
                             playlist: Playlist) -> None:
        self.cancel_queue_playlist = False
        for url in playlist:
            await self.queue_audio(author=author,
                                   voice_channel=voice_channel,
                                   text_channel=text_channel,
                                   query=url)
            if self.cancel_queue_playlist is True:
                self.queue.clear_next_queue()
                break

    async def play_audio(self) -> None:
        current_audio = self.queue.get_current_audio()
        if current_audio:
            logging.info('Playing %s', current_audio)
            await self.setup_voice_ui(audio=current_audio)
            await self.stream(audio=current_audio)

    async def setup_voice_ui(self, audio: Audio) -> None:
        await self.voice.check_voice(voice_channel=audio.voice_channel)
        self.queue.get_current_audio().end_time = datetime.now() + timedelta(seconds=audio.length)
        await self.user_interface.new_ui(text_channel=audio.text_channel)

    async def stream(self, audio: Audio) -> None:
        try:
            audio_source = PCMVolumeTransformer(FFmpegPCMAudio(source=audio.audio_url, **FFMPEG_OPTS), volume=0.1)
            loop = get_event_loop()
            await loop.run_in_executor(None, self.voice.client.play, audio_source)
        except (TypeError, AttributeError, ClientException, OpusNotLoaded) as exception:
            logging.error('Error playing audio %s: %s', audio.title, exception)
            await self.voice.disconnect_voice()

    async def change_audio(self, direction: str = 'next') -> None:
        await self.acquire_lock()
        self.start_queue_ui_tasks()

        if direction == 'prev':
            logging.info('Getting previous audio')
            await self.queue.get_previous_audio()
        elif direction == 'next':
            logging.info('Getting next audio')
            await self.queue.get_next_audio()
        else:
            logging.error('Undefined direction \'%s\', must be \'next\' or \'prev\'. Defaulting to \'next\'', direction)
            await self.queue.get_next_audio()

        await self.voice.stop_voice()
        await self.play_audio()
        await self.release_lock()

    async def reset_queue(self) -> None:
        self.cancel_queue_playlist = True
        self.queue.reset_queue()

    def start_queue_ui_tasks(self) -> None:
        self.start_check_queue()
        self.user_interface.start_auto_refresh_ui_fast()

    def start_check_queue(self) -> None:
        if not self.check_queue.is_running():
            try:
                self.check_queue.start()
            except RuntimeError as runtime_error:
                logging.debug('Auto refresh slow is already running: %s', runtime_error)

    def stop_tasks(self) -> None:
        self.check_queue.stop()
        self.user_interface.stop_tasks()

    def restart_tasks(self) -> None:
        self.check_queue.restart()
        self.user_interface.auto_refresh_ui_fast.restart()

    async def acquire_lock(self) -> None:
        while not self.lock.acquire(blocking=False):
            await sleep(0.1)

    async def release_lock(self) -> None:
        try:
            self.lock.release()
        except RuntimeError as runtime_error:
            logging.debug('Queue lock is already released, %s', runtime_error)
