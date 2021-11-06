import asyncio
import discord
from discord.ext import commands
from pytube import Playlist
import config
import getAudio
from queue import PriorityQueue
from threading import Thread

# Max file size an audio file can be, in bytes.
maxFileSize = 200000000

class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voiceClient = None
        self.audioManager = getAudio.GetAudio(maxFileSize)
        self.playAudioQueue = asyncio.PriorityQueue()
        self.songsNamesQueue = PriorityQueue()
        self.queueNumber = 0


    @commands.command()
    async def play(self, ctx, *, arg):          
        if not await self.isInVoice(ctx):
            return

        audio = self.audioManager.retrieveFile(arg)
        if not audio.results:
            print('Failed to retrieve song.')
            await ctx.send('Failed to retrieve ' + arg)
        else:        
            await self.connectToVoice(ctx)
            self.queueNumber += 1
            await self.playAudioQueue.put((self.queueNumber, self.playAudio(ctx, audio, self.playAudioQueue)))
            self.songsNamesQueue.put((self.queueNumber, audio.title))


    @commands.command()
    async def playlist(self, ctx, *, arg):          
        if not await self.isInVoice(ctx):
            return
        
        if not arg[0].find('playlist'):
            print('This is not a playlist.')
            await ctx.send('This is not a playlist.')

        playlist = Playlist(arg)

        playlistQueueNumber = self.queueNumber
        self.queueNumber += len(playlist)

        Thread(target = self.testFunction, args=(playlist.videos, playlistQueueNumber)).start()

        for url in playlist:
            playlistQueueNumber += 1
            audio = self.audioManager.retrieveFile(url)

            if not audio.results:
                print('Failed to retrieve song.')
                await ctx.send('Failed to retrieve ' + url)
            else:
                await self.connectToVoice(ctx)
                await self.playAudioQueue.put((playlistQueueNumber, self.playAudio(ctx, audio, self.playAudioQueue)))


    def testFunction(self, videos, queueNum):
        for idx, ytvid in enumerate(videos):
            self.songsNamesQueue.put((queueNum + idx, ytvid.title))


    async def playAudio(self, ctx, audio, queue=None):
        self.songsNamesQueue.get()
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Game(audio.title))
        await ctx.send('Playing {0}'.format(audio.title))

        self.voiceClient.play(discord.FFmpegPCMAudio(audio.directory))
        while self.voiceClient.is_playing():
            await asyncio.sleep(0.5)
        await self.bot.change_presence(status=discord.Status.idle)

        if queue:
            queue.task_done()


    @commands.command()
    async def queue(self, ctx):
        if not await self.isInVoice(ctx):
            return

        if self.songsNamesQueue.empty():
            await ctx.send('There are currently no songs in the queue.')
        else:
            songList = ""
            toPrint = sorted(self.songsNamesQueue.queue, key=lambda x: x[0])
            for idx, songName in enumerate(toPrint):
                songList += str(idx+1) + ') ' + songName[1] + '\n'
            await ctx.send('Song queue:\n```' + songList + '```')


    @commands.command()
    async def skip(self, ctx):
        if not await self.isInVoice(ctx):
            return

        if self.voiceClient is None or not self.voiceClient.is_playing():
            await ctx.send('Cannot skip song.')
        else:
            self.voiceClient.stop()


    @commands.command()
    async def clear(self, ctx):
        if not await self.isInVoice(ctx):
            return

        if self.voiceClient is None or not self.voiceClient.is_playing():
            await ctx.send('Cannot clear queue.')
        else:
            self.voiceClient.stop()
            self.playAudioQueue = asyncio.Queue()
            self.songsNamesQueue = PriorityQueue()


    async def connectToVoice(self, ctx):
        voiceChannel = ctx.author.voice.channel

        if self.voiceClient:
            await self.voiceClient.move_to(voiceChannel)
            await self.bot.wait_for('voice_state_update')
        else:
            self.voiceClient = await voiceChannel.connect()


    async def isInVoice(self, ctx):
        if ctx.author.voice is None:
            print('{0} is not in a voice channel'.format(ctx.author))
            await ctx.send('You must be in a voice channel to run commmands.')
            return False
        else:
            return True


    async def checkQueue(self):
        while True:
            if not self.playAudioQueue.empty():
                song = await self.playAudioQueue.get()
                await song[1]
            else:
                await asyncio.sleep(0.5)


bot = commands.Bot(command_prefix='!')
musicBot = MusicBot(bot)


@bot.event
async def on_ready():
    print('{0} logged on!'.format(bot.user))
    await musicBot.checkQueue()


@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is not None:
        print('{0} connected to voice channel {1}'.format(bot.user, after.channel.name))
    elif member == bot.user and after.channel is None:
        print('{0} left voice channel {1}'.format(bot.user, before.channel.name))


bot.add_cog(musicBot)
bot.run(config.token)