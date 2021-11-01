import asyncio
import discord
from discord import activity
from discord.ext import commands
import config
import getAudio

bot = commands.Bot(command_prefix='!')
audioManager = getAudio.getAudio()
playAudioQueue = asyncio.Queue()
songQueueNames = list()


@bot.event
async def on_ready():
    print('{0} logged on!'.format(bot.user))
    await checkQueue()

@bot.command(name='play')
async def play(ctx, *, arg):
    if ctx.author.voice is None:
        print('{0.author} is not in a voice channel'.format(ctx))
        await ctx.send('You must be in a voice channel to run this commmand.')
        return 
    
    voiceChannel = ctx.author.voice.channel
    voiceClient = bot.voice_clients[0] if len(bot.voice_clients) > 0 else None
    if voiceClient:
        await voiceClient.move_to(voiceChannel)
    else:
        voiceClient = await voiceChannel.connect()

    audio = audioManager.retrieveFile(arg)
    if not audio[0]:
        print('Failed to retrieve song.')
        await ctx.send('Failed to retrieve ' + arg)
        return

    # Queue here
    await playAudioQueue.put(playAudio(ctx, voiceClient, audio, playAudioQueue))
    songQueueNames.append(audio[1])


async def playAudio(ctx, voiceClient, audio, queue=None):
    songQueueNames.pop(0)
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(audio[1]))
    await ctx.send('Playing {0}'.format(audio[1]))
    voiceClient.play(discord.FFmpegPCMAudio(audio[2]))
    while voiceClient.is_playing():
        await asyncio.sleep(1)
    await bot.change_presence(status=discord.Status.idle)

    if queue:
        print('thread finished')
        queue.task_done()


@bot.command(name='queue')
async def queue(ctx):
    if len(songQueueNames) == 0:
        await ctx.send('There are currently no songs in the queue.')
    else:
        songList = '\n'.join(songQueueNames)
        await ctx.send('Song queue:\n' + songList)


@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is not None:
        print('Peepo connected to voice channel {0}'.format(after.channel.name))
    elif member == bot.user and after.channel is None:
        print('Peepo left voice channel {0}'.format(before.channel.name))


async def checkQueue():
    while True:
        if not playAudioQueue.empty():
            co = await playAudioQueue.get()
            await co
        else:
            await asyncio.sleep(1)

bot.run(config.token)