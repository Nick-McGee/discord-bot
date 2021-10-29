from time import sleep
import discord
from discord.voice_client import VoiceClient
import config
import getAudio


class MyClient(discord.Client):
    def __init__(self) -> None:
        self.audioManager = getAudio.getAudio()
        self.voiceClient = None

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        # Can't be the bot itself, or we'll get stuck in a loop
        if message.author == client.user:
            return

        # User requesting must in a voice channel
        if message.author.voice is None:
            await message.channel.send('Must be in voice channel to request a song.')

        if message.content.startswith('!play '):
            results = self.audioManager.retrieveFile(message.content[6:])

            if not results[0]:
                print('Failed to retrieve song.')
                await message.channel.send('Failed to retrieve song.')
                return

            print('Playing', results[1])
            await message.channel.send('Playing', results[1])

            if self.voiceClient is None:
                print('Connecting to', message.author.voice.channel)
                self.voiceClient = await message.author.voice.channel.connect()

            self.voiceClient.play(discord.FFmpegPCMAudio(source=results[2]))
            while self.voiceClient.is_playing():
                sleep(1)
            await self.voiceClient.disconnect()


client = MyClient()
client.run(config.token)