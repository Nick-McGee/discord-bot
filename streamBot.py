import asyncio
import discord
from discord import FFmpegPCMAudio
from discord.ext import commands, tasks
from youtube_dl import YoutubeDL as yt
from pytube import Playlist
import functools
import typing
import requests
import time
from queue import PriorityQueue
import os, psutil
import config

'''LOGGER'''
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


class streamBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.voice = None
        self.queuePosition = 0
        self.songQueue = PriorityQueue()
        self.isPlaying = False
        self.nowPlaying = None
        self.songThumbnail = None
        self.requestedBy = None
        self.songLength = 0
        self.clearing = False


    '''HELPERS'''
    def to_thread(func: typing.Callable) -> typing.Coroutine:
        '''
        Turns a blocking function into an async function.
        '''
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.to_thread(func, *args, **kwargs)
        return wrapper


    @to_thread
    def findAudio(self, search):
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
        
        return (info['formats'][0]['url'], info['title'], info['duration'], info['thumbnail'])
    

    async def playAudio(self, ctx, audio, title, duration, thumbnail):
        '''
        Play songs from the queue
        '''
        self.isPlaying = True
        self.nowPlaying = title
        self.songThumbnail = thumbnail
        self.requestedBy = ctx.author.display_name
        self.songLength = duration + time.mktime(time.localtime())

        print('Playing:', title)
        await self.send_message(ctx, 'green', thumbnail, True, ('Now Playing', f'{title}'), ('Length', time.strftime('%H:%M:%S', time.gmtime(duration))))

        def update(e: None):
            self.isPlaying = False
            self.nowPlaying = None
            self.songThumbnail = None
            self.requestedBy = None
            self.songLength = 0

        # Works, but can be spammy if bot disconnect.
        await self.connectToVoice(ctx)
        timeout = 0
        while timeout < 5:
            try:
                self.voice.play(FFmpegPCMAudio(audio, **FFMPEG_OPTS), after=update)
            except:
                await self.connectToVoice(ctx)
                await asyncio.sleep(3)
                timeout += 1
            else:
                timeout = 5


    async def connectToVoice(self, ctx):
        '''
        Connect the bot to a voice client.
        '''
        voiceChannel = ctx.author.voice.channel

        if self.voice:
            await self.voice.move_to(voiceChannel)
        else:
            self.voice = await voiceChannel.connect()


    async def isInVoice(self, ctx):
        '''
        Checks if the user sending a command is in a voice channel.
        '''
        if ctx.author.voice is None:
            await self.send_message(ctx, 'red', None, False, ('Error', 'You must be in a voice channel to run this command'))
            return False
        else:
            return True
    

    async def send_message(self, ctx, color, img, footer, *content):
        '''
        Send an embed to the chat.
        Can be configured with color and content.

        Example:
        await self.send_message(ctx, 'red', None, ('Error', 'Error Message'), ('Extra Details', 'Details'))
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

        if img:
            embed.set_thumbnail(url=img)
        
        if footer == True:
            embed.set_footer(text=f'Requested by {self.requestedBy}')

        await ctx.send(embed=embed)



    '''LOOPS'''
    @tasks.loop(seconds=1)
    async def checkQueue(self):
        '''
        Loop through the song queue and plays it if one is available and
        a song is not playing.
        '''
        if not self.songQueue.empty() and not self.isPlaying and not self.clearing:
            song = self.songQueue.get()
            await self.playAudio(song[1], song[2], song[3], song[4], song[5])
    

    @tasks.loop(seconds=30)
    async def bot_timeout(self):
        '''
        Disconnect bot from voice chat if it hasn't played audio
        for a certain amount of time. (currently 2mins 30 secs)
        '''
        if not self.voice or not self.voice.is_connected():
            return

        if self.voice.is_playing():
            self.voice_timeout = 0
        else:
            self.voice_timeout += 1
        
        if self.voice_timeout >= 5:
            print('Voice disconnect')
            await self.voice.disconnect()
            self.voice = None
        


    '''COMMANDS'''
    @commands.command()
    async def play(self, ctx, *, arg):
        '''
        Queue up songs.
        '''
        if not await self.isInVoice(ctx):
            return

        audio, title, duration, thumbnail = await self.findAudio(arg)
        self.queuePosition += 1
        self.songQueue.put((self.queuePosition, ctx, audio, title, duration, thumbnail))


    @commands.command()
    async def playlist(self, ctx, *, arg):
        '''
        Queue up songs from a playlist.
        '''
        if not await self.isInVoice(ctx):
            return
        
        await self.send_message(ctx, 'green', None, False, ('Downloading Playlist', 'It may take a moment to fill the queue'))

        playlist_urls = Playlist(arg)
        internalQueuePosition = self.queuePosition
        internalMaxQueuePosition = len(playlist_urls)
        self.queuePosition += internalMaxQueuePosition

        for url in playlist_urls:
            audio, title, duration, thumbnail = await self.findAudio(url)
            if self.clearing:
                return
            internalQueuePosition += 1
            self.songQueue.put((internalQueuePosition, ctx, audio, title, duration, thumbnail))


    @commands.command()
    async def now(self, ctx):
        '''
        What song is currently playing.
        '''
        if not await self.isInVoice(ctx):
            return
        
        if not self.nowPlaying:
            await self.send_message(ctx, 'orange', None, False, ('There isn\'t a song currently playing', 'Use !play or !playlist to play a song'))

        timeLeft = self.songLength - time.mktime(time.localtime())
        await self.send_message(ctx, 'green', self.songThumbnail, True, ('Now Playing', self.nowPlaying), ('Time left', time.strftime('%H:%M:%S', time.gmtime(timeLeft))))


    @commands.command()
    async def queue(self, ctx, *, arg=5):
        '''
        Show how many songs are in the queue.
        '''
        if not await self.isInVoice(ctx):
            return
                
        sortedSongs = sorted(self.songQueue.queue, key=lambda x: x[0])

        totalTime = 0
        songNames = list()
        for song in sortedSongs:
            songNames.append(song[3])
            totalTime += song[4]
        
        upNextCount = min(arg, self.songQueue.qsize())
        songNames = songNames[0:upNextCount]
        songNames = '\n'.join(songNames)

        if self.songQueue.empty():
            await self.send_message(ctx, 'orange', None, False, ('The queue is empty', 'Use !play or !playlist to play a song'))
        elif self.songQueue.qsize() == 1:
            await self.send_message(ctx, 'green', None, False, ('Queue', f'There is currently 1 song in the queue'), ('Next song', songNames), ('Total time', time.strftime('%H:%M:%S', time.gmtime(totalTime))))
        else:
            await self.send_message(ctx, 'green', None, False, ('Queue', f'There are currently {self.songQueue.qsize()} songs in the queue'), (f'Next {upNextCount} songs', songNames), ('Total time', time.strftime('%H:%M:%S', time.gmtime(totalTime))))


    @commands.command()
    async def skip(self, ctx):
        '''
        Skips the current song.
        '''
        if not await self.isInVoice(ctx):
            return

        if self.voice is None or not self.voice.is_playing():
            await self.send_message(ctx, 'orange', None, False, ('Cannot skip song', 'A song is not playing'))
        else:
            await self.send_message(ctx, 'green', None, False, ('Skipping', f'Skipping {self.nowPlaying}'))
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

        if self.voice is None or (self.songQueue.empty() and not self.isPlaying):
            await self.send_message(ctx, 'orange', None, False, ('Cannot clear queue', 'There are no songs in the queue'))
        else:
            await self.send_message(ctx, 'green', None, False, ('Clearing', 'Clearing queue of songs'))
            self.voice.stop()
            self.clearing = True
            await asyncio.sleep(4)
            self.clearing = False
            self.songQueue = PriorityQueue()


    @commands.command()
    async def stats(self, ctx):
        '''
        For internal use. Displays CPU and memory usage
        '''
        await self.send_message(ctx, 'green', None, False, ('Current memory usage', '{:.2f} MB'.format(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)), ('Current CPU usage', '{:.2f}%'.format(psutil.cpu_percent())))


    @commands.command()
    async def help(self, ctx):
        await self.send_message(ctx, 'green', None, False,
        ('Play', 'Plays a YouTube audio file. Needs a search query or YouTube URL\nExample:\n!play big iron\n!play https://www.youtube.com/watch?v=dQw4w9WgXcQ'),
        ('Playlist', 'Plays a YouTube playlist. Needs a YouTube playlist URL\nExample:\n!playlist https://www.youtube.com/playlist?list=PLlW4ryhNwVgBfFH8C_cUIjauhQUnwYy-z'),
        ('Queue', 'Displays how many songs are in the queue, the total time of queue, and the up next songs. By default up next shows a maximum of 5 songs, but it can be passed in a number to show more\nExample:\n!queue\n!queue 10'),
        ('Now', 'Displays the currently playing song, and how much time it has left\nExample:\n!now'),
        ('Skip', 'Skips the currently playing song, and will play the next song in the queue\nExample:\n!skip'),
        ('Clear', 'Clears the queue of songs and stops the currently playing song\nExample:\n!clear'))



    '''
    EVENT LISTENERS
    '''
    @commands.Cog.listener()
    async def on_ready(self):
        print('{0} logged on!'.format(self.client.user))
        if not self.checkQueue.is_running():
            self.checkQueue.start()
            self.bot_timeout.start()


    @commands.Cog.listener()
    async def on_connect(self):
        print('{0} connected!'.format(self.client.user))


    @commands.Cog.listener()
    async def on_disconnect(self):
        print('{0} disconnected!'.format(self.client.user))


    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member == self.client.user and before.channel is None:
            print('{0} connected to voice channel {1}'.format(self.client.user, after.channel.name))
        elif member == self.client.user and before.channel is not None and after.channel is not None:
            print('{0} moved from voice channel {1} to {2}'.format(self.client.user, before.channel.name, after.channel.name))
        elif member == self.client and after.channel is None:
            print('{0} left voice channel {1}'.format(self.client.user, before.channel.name))



    '''ERROR HANDLERS'''
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await self.send_message(ctx, 'red', None, False, ('Error', 'Invalid Command'))
        else:
            print(error)
    

    @play.error
    async def play_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_message(ctx, 'red', None, False, ('Error', 'You must give a search query or YouTube URL to play a video\n\nExample:\n!play big iron'))
    

    @playlist.error
    async def playlist_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_message(ctx, 'red', None, False, ('Error', 'You must give a YouTube Playlist URL to play a video\n\nExample:\n!playlist https://www.youtube.com/playlist?list=PLlW4ryhNwVgBfFH8C_cUIjauhQUnwYy-z'))
    


def main():
    bot = commands.Bot(command_prefix='!', help_command=None)
    bot.add_cog(streamBot(bot))
    bot.run(config.token)


if __name__ == '__main__':
    main()