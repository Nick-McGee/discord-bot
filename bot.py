import asyncio
import discord
from discord.ext import commands
import config
import getAudio

class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.audioManager = getAudio.getAudio()
        self.playAudioQueue = asyncio.Queue()
        self.songQueueNames = list()
        self.voiceClient = None


    @commands.command()
    async def play(self, ctx, *, arg):          
        if not await self.isInVoice(ctx):
            return

        audio = self.audioManager.retrieveFile(arg)
        if not audio[0]:
            print('Failed to retrieve song.')
            await ctx.send('Failed to retrieve ' + arg)
            return
        
        await self.connectToVoice(ctx)

        await self.playAudioQueue.put(self.playAudio(ctx, audio, self.playAudioQueue))
        self.songQueueNames.append(audio[1])


    async def playAudio(self, ctx, audio, queue=None):
        self.songQueueNames.pop(0)
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Game(audio[1]))
        await ctx.send('Playing {0}'.format(audio[1]))

        self.voiceClient.play(discord.FFmpegPCMAudio(audio[2]))
        while self.voiceClient.is_playing():
            await asyncio.sleep(0.5)
        await self.bot.change_presence(status=discord.Status.idle)

        if queue:
            queue.task_done()


    @commands.command()
    async def queue(self, ctx):
        if not await self.isInVoice(ctx):
            return

        if len(self.songQueueNames) == 0:
            await ctx.send('There are currently no songs in the queue.')
        else:
            songList = ""
            for idx, songName in enumerate(self.songQueueNames):
                songList += str(idx+1) + ') ' + songName + '\n'
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
            self.playAudioQueue = asyncio.Queue()
            self.songQueueNames = list()
            self.voiceClient.stop()


    async def connectToVoice(self, ctx):
        voiceChannel = ctx.author.voice.channel
        self.voiceClient = self.bot.voice_clients[0] if len(self.bot.voice_clients) > 0 else None
        if self.voiceClient:
            await self.voiceClient.move_to(voiceChannel)
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
                await song
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