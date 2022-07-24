<h1 align="center">Discord Music Bot</h1>

<div align="center">
  
[![HitCount](https://hits.dwyl.com/Nick-McGee/discord-bot.svg?style=flat)](http://hits.dwyl.com/Nick-McGee/discord-bot)
<a href="https://hub.docker.com/repository/docker/nrmcgee/discord-bot" target="_blank" rel="noopener noreferrer">![Workflow](https://github.com/Nick-McGee/discord-bot/actions/workflows/main.yml/badge.svg)</a>
  
</div>

## What is it?
This is a Discord bot built on <a href="https://github.com/Pycord-Development/pycord">Pycord 2.0</a>. The bot plays audio from a Youtube URL or search query. It is controlled with slash commands and the message-based user-interface. The bot is only intended to work on one Discord server (guild).

### Commands
+ **play** - Queue YouTube audio files via a search query or URL
+ **play_next** - Queue up next YouTube audio files via a search query or URL
+ **playlist** - Queue a series of audio files from a YouTube Playlist URL
+ **restart_queue** - Start playing from the beginning of the previous queue
+ **go_to** - Go to a specific time in the audio. If no time is set, the audio is reset to the start
+ **clear_queue** - Clear the up next queue
+ **clear_previous_queue** - Clear the previous queue
+ **remove** - Skips and removes the currently playing song from the queue
+ **reset** - Reset the voice client, queue, and user interface
+ **reconnect_bot** - Reconnect the bot to your voice channel and text channel

### UI

<div align="center">

![A screenshot showing the bot's UI, with the song title, time remaining, image, queue, and the back and forth buttons.](/screenshots/ui.png?raw=true "A screenshot showing the bot's UI")

</div>

### Demo

<div align="center">

[![Quick Discord Bot Demo Video](http://img.youtube.com/vi/TuIMTAzkWHY/0.jpg)](http://www.youtube.com/watch?v=TuIMTAzkWHY "Quick Discord Bot Demo")

</div>

## How to use it?
+ <a href="https://docs.pycord.dev/en/master/discord.html#:~:text=Make%20sure%20you're%20logged%20on%20to%20the%20Discord%20website.&text=Click%20on%20the%20%E2%80%9CNew%20Application,and%20clicking%20%E2%80%9CAdd%20Bot%E2%80%9D.">**Create a Discord Bot** and invite it to your Discord server</a>

### Build and Run with Docker (Recommended)
#### Build and run the image locally
+ Build the image with `docker build -t python-bot .` in the root directory
+ Run the bot with `docker run -e BOT_TOKEN=<YOUR BOT TOKEN> -e GUILD_ID=<YOUR GUILD ID> python-bot` in the root directory

#### Deploy and run the image on the cloud
+ Get the latest docker image built from the `main` branch from https://hub.docker.com/repository/docker/nrmcgee/discord-bot
+ Deploy the image on a cloud service (I personally use a Google Cloud Compute Engine VM)

### Running from source
+ Install FFMPEG if it is not on your system
+ (Recommended) Create a virtual environment
+ Install the dependencies from `requirements.txt` with `pip install -r requirements.txt` in the root directory
+ Set an environment variable for BOT_TOKEN with your bot's token
+ Set an environment variable for GUILD_ID with the Discord guild id (server) you wish to deploy the bot on
+ Run the bot with `python src/bot.py` in the root directory
