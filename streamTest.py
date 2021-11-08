import discord
from youtube_dl import YoutubeDL as yt
import requests
from discord import FFmpegPCMAudio
from discord.ext import commands
from discord.utils import get
from queue import PriorityQueue
import config

FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
bot = commands.Bot(command_prefix='!')
voice = None

def searchVideo(query):
    with yt({'format': 'bestaudio', 'age_limit': '21', 'noplaylist': 'True'}) as ytdl:
        try:
            requests.get(query)
        except:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        else:
            info = ytdl.extract_info(query, download=False)
    return (info, info['formats'][0]['url'])


@bot.command()
async def play(ctx, *, query):
    global voice
    video, source = searchVideo(query)

    await join(ctx)

    embed = discord.Embed(
        color = discord.Color.green()
    )

    embed.add_field(name='Now Playing', value=video['title'])

    await ctx.send(embed=embed)
    await ctx.send('Now playing: {0}'.format(video['title']))
    await ctx.send('Length: {0}'.format(video['duration'] / 60))

    voice.play(FFmpegPCMAudio(source, **FFMPEG_OPTS))
    voice.is_playing()


async def join(ctx):
    voiceChannel = ctx.author.voice.channel

    global voice
    if voice:
        await voice.move_to(voiceChannel)
        await bot.wait_for('voice_state_update')
    else:
        voice = await voiceChannel.connect()


bot.run(config.token)
