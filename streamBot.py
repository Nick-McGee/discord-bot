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
        self.queuePosition = 0
        self.songQueue = PriorityQueue()
        self.isPlaying = False
        self.nowPlaying = None
        self.songLength = 0


    @tasks.loop(seconds=1)
    async def checkQueue(self):
        '''
        Loop through the song queue and play it if it can.
        '''
        if not self.songQueue.empty() and self.isPlaying is False:
            print('Queue pulled a song.')
            song = self.songQueue.get()
            await self.playAudio(song[1], song[2], song[3], song[4])


    @commands.command()
    async def play(self, ctx, *, arg):
        '''
        Queue up queries.
        '''
        if not await self.isInVoice(ctx):
            return
        await self.connectToVoice(ctx)

        audio, title, duration = await self.findAudio(arg)
        self.queuePosition += 1
        self.songQueue.put((self.queuePosition, ctx, audio, title, duration))


    @commands.command()
    async def playlist(self, ctx, *, arg):
        '''
        Queue up queries from playlist.
        '''
        if not await self.isInVoice(ctx):
            return
        
        await self.send_message(ctx, 'green', ('Downloading Playlist', 'This may take a moment'))

        with yt({'format': 'bestaudio', 'age_limit': '21'}) as ytdl:
            try:
                ytdl.cache.clear()
            except:
                print('No cache to clear.')

            try:
                requests.get(arg)
                results = ytdl.extract_info(arg, download=False)
            except:
                await self.send_message(ctx, 'red', ('Error', 'Unable to retrieve playlist'))

            entries = results['entries']

            internalQueuePosition = 0
            internalMaxQueuePosition = len(entries)
            self.queuePosition += internalMaxQueuePosition

            for entry in entries:
                self.songQueue.put((internalQueuePosition, ctx, entry['formats'][0]['url'], entry['title'], entry['duration']))
                internalQueuePosition += 1


    async def findAudio(self, search):
        '''
        Stream audio from youtube either by search query or by URL
        '''
        with yt({'format': 'bestaudio', 'age_limit': '21', 'noplaylist': 'True'}) as ytdl:
            try:
                ytdl.cache.clear()
                requests.get(search)
            except:
                info = ytdl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            else:
                info = ytdl.extract_info(search, download=False)
        return (info['formats'][0]['url'], info['title'], info['duration'])


    async def playAudio(self, ctx, audio, title, duration):
        '''
        Play songs from the queue
        '''
        self.isPlaying = True

        await self.connectToVoice(ctx)
        await self.send_message(ctx, 'green', ('Now Playing', f'{title}'), ('Length', time.strftime('%H:%M:%S', time.gmtime(duration))))
        self.nowPlaying = title
        self.songLength = duration + time.mktime(time.localtime())

        def update(e: None):
            self.nowPlaying = None
            self.songLength = 0
            self.isPlaying = False
        self.voice.play(FFmpegPCMAudio(audio, **FFMPEG_OPTS), after=update)


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
            await self.send_message(ctx, 'orange', ('The queue is empty', 'Use !play or !playlist to play a song'))
        elif self.songQueue.qsize() == 1:
            await self.send_message(ctx, 'green', ('Queue', f'There is currently 1 song in the queue'), ('Next song', songNames), ('Total time', time.strftime('%H:%M:%S', time.gmtime(totalTime))))
        else:
            await self.send_message(ctx, 'green', ('Queue', f'There are currently {self.songQueue.qsize()} songs in the queue'), (f'Next {upNextCount} songs', songNames), ('Total time', time.strftime('%H:%M:%S', time.gmtime(totalTime))))


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
            self.songQueue = PriorityQueue()
            await self.send_message(ctx, 'green', ('Clearing', 'Cleared queue of songs'))
            self.voice.stop()


    @commands.command()
    async def debug(self, ctx):
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