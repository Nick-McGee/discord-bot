from time import sleep
import discord
from discord.voice_client import VoiceClient
import config
import downloadAudio


class MyClient(discord.Client):
    voiceClient = None

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.author == client.user:
            return

        if message.author.voice is None:
            await message.channel.send('Must be in voice channel to request a song.')

        if message.content.startswith('!play '):
            print('Downloading', message.content[6:])

            if self.voiceClient is None:
                print('Connecting to', message.author.voice.channel)
                self.voiceClient = await message.author.voice.channel.connect()

            downloadAudio.download(message.content[6:])
            self.voiceClient.play(discord.FFmpegPCMAudio(
                source='music/YEAH_BOI.mp3'))
            while self.voiceClient.is_playing():
                sleep(.1)
            await self.voiceClient.disconnect()


client = MyClient()
client.run(config.token)
