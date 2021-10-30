import asyncio
from time import sleep
import traceback
import discord
from discord import member
from discord.ext import tasks, commands
from discord.ext.commands.core import after_invoke
import config
import getAudio

bot = commands.Bot(command_prefix='!')
audioManager = getAudio.getAudio()
songQueue = list()
playing = False

@bot.event
async def on_ready():
    print('{0.user} logged on!'.format(bot))

@bot.command(name='play')
async def play(ctx, *, arg):
    try:
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
        
        songQueue.append((audio[1], audio[2]))
        await playAudio(ctx, voiceClient)

    except Exception:
        traceback.print_exc()


async def playAudio(ctx, voiceClient):
    global playing
    if playing:
        return

    while len(songQueue) > 0:
        song = songQueue.pop(0)
        await ctx.send('Playing {0}'.format(song[0]))

        playing = True
        voiceClient.play(discord.FFmpegPCMAudio(song[1]))

        while voiceClient.is_playing():
            await asyncio.sleep(2)

    playing = False
    print('thread finished')


@bot.command(name='queue')
async def queue(ctx):
    if len(songQueue) == 0:
        await ctx.send('There are currently no songs in the queue.')
    else:
        songList = [song[0] for song in songQueue]
        songList = '\n'.join(songList)
        await ctx.send('Song queue:\n' + songList)


@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is not None:
        print('Peepo connected to voice channel {0}'.format(after.channel.name))
    elif member == bot.user and after.channel is None:
        print('Peepo left voice channel {0}'.format(before.channel.name))

bot.run(config.token)