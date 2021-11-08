from asyncio.queues import PriorityQueue
from youtube_dl import YoutubeDL
from requests import get
import discord
from discord import FFmpegPCMAudio
from discord.ext import commands
from discord.utils import get
import config
from streamTest import play

class MusicBot(commands.Cog):
    def __init__(self):
        self.queue = PriorityQueue()
        self.nowPlaying = None


    @commands.command()
    async def play(ctx, *, arg):
        '''
        Queue up queries.
        '''
        pass


    @commands.command()
    async def playlist(ctx, *, arg):
        '''
        Queue up queries from playlist.
        '''
        pass


    def playAudio():
        '''
        Play songs from the queue
        '''
        pass


    @commands.command()
    async def now(ctx, *, arg):
        '''
        How many songs are now playing.
        '''
        pass


    @commands.command()
    async def queue(ctx, *, arg):
        '''
        Show how many songs are in the queue.
        '''
        pass


    @commands.command()
    async def clear(ctx, *, arg):
        '''
        Stop the current song and clear the song queue.
        No songs should play after this cmd is run, until another song
        is queued.
        '''
    pass


    @commands.command()
    async def debug(ctx, *, arg):
        '''
        For internal use. Should display memory and CPU usage.
        '''
        pass


    async def send_message(ctx, color, content):
        '''
        Send an embed to the chat.
        Can be configured with color and content
        '''
        pass



bot = commands.Bot(command_prefix='!')
musicBot = MusicBot(bot)
bot.add_cog(musicBot)
bot.run(config.token)