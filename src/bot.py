from discord import Bot

from audio_streamer import AudioStreamer

from config.auth import BOT_TOKEN


if __name__ == '__main__':
    bot = Bot()
    bot.add_cog(AudioStreamer(bot=bot))
    bot.run(BOT_TOKEN)
