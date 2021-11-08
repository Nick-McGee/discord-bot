import discord
from youtube_dl import YoutubeDL as yt
import requests
from discord import FFmpegPCMAudio
from discord.ext import commands, tasks
from discord.utils import get
from queue import PriorityQueue
import time
import config

FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
bot = commands.Bot(command_prefix='!')
voice = None
songQueue = list()
playing = False

def searchVideo(query):
    with yt({'format': 'bestaudio', 'age_limit': '21', 'noplaylist': 'True'}) as ytdl:
        try:
            requests.get(query)
        except:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        else:
            info = ytdl.extract_info(query, download=False)
    return (info, info['formats'][0]['url'])


@tasks.loop(seconds=1)
async def checkQueue():
    if len(songQueue) > 0 and playing is False:
        print('Queue pulled a song.')
        song = songQueue.pop(0)
        await _play(song[0], song[1])


@bot.command()
async def play(ctx, *, query):
    songQueue.append((ctx, query))


async def _play(ctx, query):
    global playing
    playing = True
    global voice
    video, source = searchVideo(query)

    await join(ctx)

    embed = discord.Embed(color = discord.Color.green())
    embed.add_field(name='Now Playing', value=video['title'], inline=False)
    embed.add_field(name='Length', value='{0}'.format(time.strftime('%H:%M:%S', time.gmtime(video['duration']))), inline=False)
    await ctx.send(embed=embed)

    def update(e: None):
        global playing
        playing = False

    voice.play(FFmpegPCMAudio(source, **FFMPEG_OPTS), after=update)


async def join(ctx):
    voiceChannel = ctx.author.voice.channel

    global voice
    if voice:
        await voice.move_to(voiceChannel)
        await bot.wait_for('voice_state_update')
    else:
        voice = await voiceChannel.connect()


@bot.event
async def on_ready():
    print('bot started')
    if not checkQueue.is_running():
        checkQueue.start()


bot.run(config.token)
