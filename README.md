# Discord Music Bot

This is a Discord music bot that plays music in voice channels. The bot uses YouTube as its source and allows users to queue and play songs upon user request. It also continuously plays music based on user selection.

## Setup

To run this bot, you need to have Python and `pip` installed on your system. Additionally, you need to create a virtual environment and install the required dependencies.

### Step-by-Step Instructions

1. **Clone the Repository**

   ```sh
   git clone https://github.com/Blackkingsman/DiscordMusicBot.git
   cd DiscordMusicBot
   ```

2. **Create a Virtual Environment**

   Create and activate a virtual environment:

   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**

   Install the required Python packages:

   ```sh
   pip install discord.py yt-dlp python-dotenv
   ```

4. **Set Up the `.env` File**

   Create a `.env` file in the root directory of the project and add the following lines:

   ```plaintext
   DISCORD_BOT_TOKEN=your-discord-bot-token
   VOICE_CHANNEL_ID=your-voice-channel-id
   ```

   Replace `your-discord-bot-token` with your actual Discord bot token and `your-voice-channel-id` with the ID of the voice channel where the bot will connect.

5. **Retrieve Your Discord Bot Token**

   1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
   2. Click on "New Application".
   3. Name your application and click "Create".
   4. Navigate to the "Bot" tab on the left sidebar.
   5. Click "Add Bot" and confirm.
   6. Under the "Token" section, click "Copy" to copy your bot token. Paste this token in your `.env` file as `DISCORD_BOT_TOKEN`.

6. **Enable Privileged Gateway Intents**

   Some Gateway Intents require approval if your bot is verified. If your bot is not verified, you can toggle these intents to access them:

   - **Presence Intent**: Required for your bot to receive Presence Update events. Note that once your bot reaches 100 or more servers, this will require verification and approval. Read more [here](https://discord.com/developers/docs/topics/gateway#privileged-intents).
   - **Server Members Intent**: Required for your bot to receive events listed under GUILD_MEMBERS. Note that once your bot reaches 100 or more servers, this will require verification and approval. Read more [here](https://discord.com/developers/docs/topics/gateway#privileged-intents).
   - **Message Content Intent**: Required for your bot to receive message content in most messages. Note that once your bot reaches 100 or more servers, this will require verification and approval. Read more [here](https://discord.com/developers/docs/topics/gateway#privileged-intents).

   Enable these intents in the "Privileged Gateway Intents" section on the "Bot" tab.

7. **Generate OAuth2 URL for Your Bot**

   1. Navigate to the "OAuth2" tab on the left sidebar.
   2. Under the "OAuth2 URL Generator" section, select the following scopes:
      - `bot`
      - `applications.commands`
   3. Under "Bot Permissions", select the permissions your bot needs. For example:
      - `Send Messages`
      - `Connect`
      - `Speak`
   4. Copy the generated URL and paste it into your browser to add the bot to your server.

8. **Run the Bot**

   Run the bot using the following command:

   ```sh
   python hiphop-bot.py
   ```

## How It Works

### Main Features

- **Play Music on Request**: Users can request the bot to play specific songs by providing YouTube URLs or search queries.
- **Continuous Playback**: The bot ensures continuous playback by playing a default hip hop radio mix when there are no user requests in the queue.

### Code Explanation and Customization

1. **Loading Environment Variables**: The bot loads the Discord bot token and voice channel ID from a `.env` file using the `dotenv` package.
2. **Initializing the Bot**: The bot is initialized with the required intents to read messages and interact with voice channels.
3. **YouTube Downloading**: The `yt_dlp` package is used to download audio from YouTube.
4. **Handling Commands**: The bot listens for specific commands (`play`, `search`, `join`, `leave`, `info`, `queue`) and performs actions accordingly.
5. **Playing Music**: Songs are queued and played using `discord.FFmpegPCMAudio`. If the queue is empty, the bot plays a default hip hop radio mix to ensure continuous playback.

### Customizing the Default Continuous Playback

To customize the default music that plays when the queue is empty, modify the search query in the `search_and_play_hip_hop` function. Locate the following line in `hiphop-bot.py`:

```python
results = await bot.loop.run_in_executor(None, lambda: YTDLSource.ytdl.extract_info("ytsearch1:Dance Radio Hits 2024' Dance Music 2024 - Top Hits 2024 Hip Hop, Rap R&B Songs 2024 Best Music 2024", download=False))
```

Change the search query `"Dance Radio Hits 2024' Dance Music 2024 - Top Hits 2024 Hip Hop, Rap R&B Songs 2024 Best Music 2024"` to your desired search term.

## Running the Bot in the Background

To run the bot in the background, you can use the `nohup` command. This is useful if you want the bot to continue running even after you log out of the terminal session.

### Run with `nohup`

```sh
nohup python hiphop-bot.py &
```

The `nohup` command allows the bot to run in the background, and the `&` at the end of the command puts it in the background. This way, the bot will keep running even if the terminal session is closed.

## Commands

The bot responds to the following commands:

- `@bot play <url>`: Add a song to the queue and play it.
- `@bot search <query>`: Search for a song to play.
- `@bot join`: Make the bot join your voice channel.
- `@bot leave`: Make the bot leave your voice channel and return to the original channel.
- `@bot info`: Show the help message with available commands.
- `@bot queue`: Show the current song queue.

## Contributing

If you want to contribute to this project, please fork the repository and create a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for 
