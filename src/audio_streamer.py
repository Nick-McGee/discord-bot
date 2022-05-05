import logging
from typing import Union
from asyncio import get_event_loop, all_tasks

from discord import Bot, ApplicationContext, ClientException, TextChannel, User, Member, VoiceChannel, Embed, Colour
from discord.ext import commands
from discord.commands import Option, slash_command
from discord.errors import HTTPException
from pytube import Playlist

from audio import Audio, AudioQueue
from voice import Voice
from audio_streamer_user_interface import StreamerUserInterface
from youtube_client import get_audio, get_playlist
import config.logger
from config.settings import DELETE_TIMER
from config.auth import GUILD_ID

green = Colour.green()
red = Colour.red()


class AudioStreamer(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.voice = Voice(bot = bot, after_function = self.change_audio)
        self.queue = AudioQueue(event_loop = get_event_loop())
        self.user_interface = StreamerUserInterface(change_audio_function = self.change_audio,
                                                    queue = self.queue)

    @slash_command(name='play', description='Queue YouTube audio files via a search query or URL', guild_ids=[GUILD_ID])
    async def play_command(self, ctx: ApplicationContext, query: Option(str, 'Search or URL')) -> None:
        logging.info('Play command invoked')
        audio_title = await self.queue_audio(author=ctx.author,
                                             voice_channel=ctx.author.voice.channel,
                                             text_channel=ctx.channel,
                                             query=query)
        if audio_title:
            await ctx.respond(embed=Embed(title='Queued', description=f'**{audio_title}**', color=green),
                              delete_after=DELETE_TIMER)
        else:
            await ctx.respond(embed=Embed(title='Error', description=f'Unable to queue **{query}**', color=red),
                              delete_after=DELETE_TIMER)

    @slash_command(name='play_next', description='Queue up next YouTube audio files via a search query or URL', guild_ids=[GUILD_ID])
    async def play_next_command(self, ctx: ApplicationContext, query: Option(str, 'Search or URL')) -> None:
        logging.info('Play next command invoked')
        audio_title = await self.queue_audio(author=ctx.author,
                                             voice_channel=ctx.author.voice.channel,
                                             text_channel=ctx.channel,
                                             query=query,
                                             add_to_start=True)
        if audio_title:
            await ctx.respond(embed=Embed(title='Queued Next', description=f'**{audio_title}**', color=green),
                              delete_after=DELETE_TIMER)
        else:
            await ctx.respond(embed=Embed(title='Error', description=f'Unable to queue next **{query}**', color=red),
                              delete_after=DELETE_TIMER)

    @slash_command(name='playlist', description='Queue a series of audio files from a YouTube Playlist URL', guild_ids=[GUILD_ID])
    async def playlist_command(self, ctx: ApplicationContext, url: Option(str, 'A playlist URL')) -> None:
        logging.info('Playlist command invoked')
        playlist = get_playlist(playlist_url=url)
        try:
            if len(playlist) == 0:
                await ctx.respond(embed=Embed(title='Error', description=f'Unable to queue playlist **{url}**', color=red),
                                  delete_after=DELETE_TIMER)
            else:
                await ctx.respond(embed=Embed(title='Queuing Playlist',
                                              description=playlist.title,
                                              color=Colour.green()),
                                  delete_after=DELETE_TIMER)

                get_event_loop().create_task(coro=self.queue_playlist(author=ctx.author,
                                                                      voice_channel=ctx.author.voice.channel,
                                                                      text_channel=ctx.channel,
                                                                      playlist=playlist),
                                             name='playlist')

        except KeyError as key_error:
            logging.error('Key error queuing playlist: %s', key_error)
            await ctx.respond(embed=Embed(title='Error', description=f'Unable to queue playlist **{url}**', color=red),
                              delete_after=DELETE_TIMER)

    @slash_command(name='restart_queue', description='Start playing from the beginning of the previous queue', guild_ids=[GUILD_ID])
    async def restart_queue(self, ctx: ApplicationContext) -> None:
        logging.info('Restart queue command invoked')
        await self.queue.restart_queue()
        await ctx.respond(embed=Embed(title='Restarted Queue', color=green),
                          delete_after=DELETE_TIMER)

    @slash_command(name='clear_queue', description='Clear the up next queue', guild_ids=[GUILD_ID])
    async def clear_up_next_command(self, ctx: ApplicationContext) -> None:
        logging.info('Clear command invoked')
        self.cancel_playlist()
        self.queue.clear_next_queue()
        await ctx.respond(embed=Embed(title='Cleared Up Next Queue', color=green),
                          delete_after=DELETE_TIMER)

    @slash_command(name='clear_previous_queue', description='Clear the previous queue', guild_ids=[GUILD_ID])
    async def clear_previous_command(self, ctx: ApplicationContext) -> None:
        logging.info('Clear command invoked')
        self.queue.clear_previous_queue()
        await ctx.respond(embed=Embed(title='Cleared Previous Queue', color=green),
                          delete_after=DELETE_TIMER)

    @slash_command(name='remove', description='Skips and removes the currently playing song from the queue', guild_ids=[GUILD_ID])
    async def remove_command(self, ctx: ApplicationContext) -> None:
        logging.info('Remove from queue command invoked')
        audio_title = self.queue.remove_current_audio()
        if audio_title:
            await ctx.respond(embed=Embed(title='Remove from Queue', description=f'Removed **{audio_title}**', color=green),
                              delete_after=DELETE_TIMER)
        else:
            await ctx.respond(embed=Embed(title='Unable to Remove from Queue', description='Unable to find current audio to remove', color=red),
                              delete_after=DELETE_TIMER)

    @slash_command(name='reset', description='Reset the voice client, queue, and user interface', guild_ids=[GUILD_ID])
    async def reset_command(self, ctx: ApplicationContext) -> None:
        logging.info('Reset command invoked')
        self.cancel_playlist()
        self.queue.reset_queue()

        await self.voice.disconnect_voice()

        ctx_message_id = await self.get_id_from_ctx(ctx=ctx)
        await self.user_interface.delete_ui(bot=self.bot, guild=ctx.guild, ignore_msg_ids={ctx_message_id})

        await ctx.respond(embed=Embed(title='Reset Bot',
                                      description=f'**{self.bot.user.display_name}** has been reset',
                                      color=green),
                          delete_after=DELETE_TIMER)

    @slash_command(name='reconnect_bot', description='Reconnect the bot to your voice channel and text channel', guild_ids=[GUILD_ID])
    async def reconnect_bot(self, ctx: ApplicationContext) -> None:
        logging.info('Reconnect command invoked')
        try:
            await self.voice.join_voice(voice_channel=ctx.author.voice.channel)
            await self.user_interface.new_ui(data=ctx.channel)
            await ctx.respond(embed=Embed(title='Reconnected',
                                          description=f'''**{self.bot.user.display_name}** connected to voice channel **{ctx.author.voice.channel}**
                                                          and text channel **{ctx.channel}**''',
                                          color=green),
                              delete_after=DELETE_TIMER)
            logging.info('Bot reconnected')
        except AttributeError as attribute_error:
            logging.error('Unable to connect bot to voice: %s', attribute_error)
            await ctx.respond(embed=Embed(title='Unable to Connect', description=f'Error connecting **{self.bot.user.display_name}** to voice', color=red),
                              delete_after=DELETE_TIMER)

    @commands.Cog.listener()
    async def on_ready(self):
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
    async def defer_and_check_voice(self, ctx: ApplicationContext) -> None:
        await ctx.defer()
        if ctx.author and ctx.author.voice is None:
            await ctx.respond(embed=Embed(title='Error', description='You are not connected to a voice channel', color=red),
                              delete_after=DELETE_TIMER)

    def change_audio(self, previous: bool = False) -> None:
        if previous:
            logging.info('Getting previous audio')
            self.queue.get_previous_audio()
        else:
            logging.info('Getting next audio')
            self.queue.get_next_audio()

    async def queue_audio(self,
                          query: str,
                          author: Union[User, Member],
                          voice_channel: VoiceChannel,
                          text_channel: TextChannel,
                          add_to_start: bool = False) -> Union[str, None]:
        logging.info('Queuing %s', query)
        entry = await get_event_loop().run_in_executor(None, get_audio, query)

        title = None
        if entry:
            audio = Audio(author=author,
                          voice_channel=voice_channel,
                          text_channel=text_channel,
                          audio_url=entry['audio_url'],
                          webpage_url=entry['webpage_url'],
                          title=entry['title'],
                          length=entry['length'],
                          thumbnail=entry['thumbnail'])

            if add_to_start:
                await self.queue.append_left(audio=audio)
            else:
                await self.queue.append(audio=audio)

            await self.user_interface.refresh_ui()
            logging.info('Queued %s %s', audio.title, audio.audio_url)

            title = entry['title']
        else:
            logging.error('Unable to queue audio %s', query)
        return title

    async def queue_playlist(self,
                             author: Union[User, Member],
                             voice_channel: VoiceChannel,
                             text_channel: TextChannel,
                             playlist: Playlist) -> None:
        for url in playlist:
            await self.queue_audio(author=author,
                                   voice_channel=voice_channel,
                                   text_channel=text_channel,
                                   query=url)

    @classmethod
    def cancel_playlist(cls) -> None:
        tasks = [task for task in all_tasks() if task.get_name() == 'playlist']
        for task in tasks:
            task.cancel()

    @staticmethod
    async def get_id_from_ctx(ctx: ApplicationContext):
        try:
            ctx_message = await ctx.interaction.original_message()
            ctx_message_id = ctx_message.id
        except (HTTPException, ClientException) as msg_not_found:
            logging.error('Unable to find message: %s', msg_not_found)
            ctx_message_id = None
        return ctx_message_id
