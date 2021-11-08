import time
from youtube_dl import YoutubeDL as yt
import requests
import discord
from discord import FFmpegPCMAudio
from discord.ext import commands, tasks
from queue import PriorityQueue
import config


FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


class streamBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.voice = None
        self.songQueue = list()
        self.isPlaying = False
        self.nowPlaying = None
        self.songLength = 0


    @tasks.loop(seconds=1)
    async def checkQueue(self):
        '''
        Loop through the song queue and play it if it can.
        '''
        if len(self.songQueue) > 0 and self.isPlaying is False:
            print('Queue pulled a song.')
            song = self.songQueue.pop(0)
            await self.playAudio(song[0], song[1])


    @commands.command()
    async def play(self, ctx, *, arg):
        '''
        Queue up queries.
        '''
        print('queued a song!')
        if not await self.isInVoice(ctx):
            return
        self.songQueue.append((ctx, arg))


    @commands.command()
    async def playlist(self, ctx, *, arg):
        '''
        Queue up queries from playlist.
        '''
        if not await self.isInVoice(ctx):
            return
        pass


    async def findAudio(self, search):
        '''
        Stream audio from youtube either by search query or by URL
        '''
        with yt({'format': 'bestaudio', 'age_limit': '21', 'noplaylist': 'True'}) as ytdl:
            try:
                requests.get(search)
            except:
                info = ytdl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            else:
                info = ytdl.extract_info(search, download=False)
        return (info, info['formats'][0]['url'])


    async def playAudio(self, ctx, search):
        '''
        Play songs from the queue
        '''
        self.isPlaying = True
        video, source = await self.findAudio(search)

        await self.connectToVoice(ctx)
        await self.send_message(ctx, 'green', ('Now Playing', f'{video["title"]}'), ('Length', time.strftime('%H:%M:%S', time.gmtime(video['duration']))))
        self.nowPlaying = video['title']
        self.songLength = video['duration'] + time.mktime(time.localtime())

        def update(e: None):
            self.nowPlaying = None
            self.songLength = 0
            self.isPlaying = False
        self.voice.play(FFmpegPCMAudio(source, **FFMPEG_OPTS), after=update)


    async def connectToVoice(self, ctx):
        '''
        Connect the bot to a voice client.
        '''
        voiceChannel = ctx.author.voice.channel

        if self.voice:
            await self.voice.move_to(voiceChannel)
            await bot.wait_for('voice_state_update')
        else:
            self.voice = await voiceChannel.connect()


    @commands.command()
    async def now(self, ctx):
        '''
        What song is currently playing.
        '''
        if not await self.isInVoice(ctx):
            return
        
        if not self.nowPlaying:
            await self.send_message(ctx, 'orange', ('There isn\'t a song currently playing', 'Use !play or !playlist to play a song'))

        timeLeft = self.songLength - time.mktime(time.localtime())
        await self.send_message(ctx, 'green', ('Now Playing', self.nowPlaying), ('Time left', time.strftime('%H:%M:%S', time.gmtime(timeLeft))))


    @commands.command()
    async def queue(self, ctx):
        '''
        Show how many songs are in the queue.
        '''
        if not await self.isInVoice(ctx):
            return
        
        if len(self.songQueue) <= 0:
            await self.send_message(ctx, 'orange', ('The queue is empty', 'Use !play or !playlist to play a song'))
        else:
            await self.send_message(ctx, 'green', ('Queue', f'There are currently {len(self.songQueue)} songs in the queue'))


    @commands.command()
    async def skip(self, ctx):
        '''
        Skips the current song.
        '''
        if not await self.isInVoice(ctx):
            return

        if self.voice is None or not self.voice.is_playing():
            await self.send_message(ctx, 'orange', ('Cannot skip song', 'A song is not playing'))
        else:
            await self.send_message(ctx, 'green', ('Skipping', f'Skipping {self.nowPlaying}'))
            self.voice.stop()


    @commands.command()
    async def clear(self, ctx):
        '''
        Stop the current song and clear the song queue.
        No songs should play after this cmd is run, until another song
        is queued.
        '''
        if not await self.isInVoice(ctx):
            return

        if self.voice is None or not self.voice.is_playing():
            await self.send_message(ctx, 'orange', ('Cannot clear queue', 'There are no songs in the queue'))
        else:
            self.songQueue = list()
            await self.send_message(ctx, 'green', ('Clearing', 'Cleared queue of songs'))
            self.voice.stop()


    @commands.command()
    async def debug(self, ctx, *, arg):
        '''
        For internal use. Should display memory and CPU usage.
        '''
        pass


    async def send_message(self, ctx, color, *content):
        '''
        Send an embed to the chat.
        Can be configured with color and content.

        Example:
        await self.send_message(ctx, 'red', ('Error', 'Error Message'), ('Extra Details', 'Details'))
        '''
        embed = discord.Embed()
        if color == 'green':
            embed.color = discord.Color.green()
        elif color == 'orange':
            embed.color = discord.Color.orange()
        elif color == 'red':
            embed.color = discord.Color.red()
        else:
            embed.color = discord.Color.darker_gray()
        
        for name, value in content:
            embed.add_field(name=name, value=value, inline=False)

        await ctx.send(embed=embed)



    '''
    EVENT LISTENERS AND CHECKS
    '''
    @commands.Cog.listener()
    async def on_ready(self):
        print('{0} logged on!'.format(self.client.user))
        if not self.checkQueue.is_running():
            self.checkQueue.start()


    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member == self.client.user and before.channel is None:
            print('{0} connected to voice channel {1}.'.format(self.client.user, after.channel.name))
        elif member == self.client.user and before.channel is not None and after.channel is not None:
            print('{0} moved from voice channel {1} to {2}.'.format(self.client.user, before.channel.name, after.channel.name))
        elif member == bot.user and after.channel is None:
            print('{0} left voice channel {1}.'.format(self.client.user, before.channel.name))


    # Might not need this
    # https://www.youtube.com/watch?v=_2ifplRzQtM
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_message(ctx, 'red', ('Error', 'Missing Required Argument'))
        elif isinstance(error, commands.CommandNotFound):
            await self.send_message(ctx, 'red', ('Error', 'Invalid Command'))
    
    
    async def isInVoice(self, ctx):
        if ctx.author.voice is None:
            await self.send_message(ctx, 'red', ('Error', 'You must be in a voice channel to run this command'))
            return False
        else:
            return True



bot = commands.Bot(command_prefix='!')
bot.add_cog(streamBot(bot))
bot.run(config.token)