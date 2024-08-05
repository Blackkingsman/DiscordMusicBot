import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os


# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
VOICE_CHANNEL_ID = int(os.getenv('VOICE_CHANNEL_ID'))

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Global queue for songs
song_queue = []
current_song = None
MAX_PLAY_TIME = 600
waiting_for_selection = False
search_results_cache = {}
waiting_user_id = None
hip_hop_playing = False
song_playing = False
original_voice_channel = None

class YTDLSource(discord.PCMVolumeTransformer):
    ytdl_format_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'
    }

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        retries = 3  # Number of retries
        for attempt in range(retries):
            try:
                loop = loop or asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(url, download=not stream))
                if 'entries' in data:
                    data = data['entries'][0]
                filename = data['url'] if stream else cls.ytdl.prepare_filename(data)
                return cls(discord.FFmpegPCMAudio(filename, **cls.ffmpeg_options), data=data)
            except Exception as e:
                if attempt < retries - 1:
                    print(f"Retrying {attempt + 1}/{retries} after error: {e}")
                    await asyncio.sleep(2)
                else:
                    raise e

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    channel = bot.get_channel(VOICE_CHANNEL_ID)
    global original_voice_channel
    if channel and isinstance(channel, discord.VoiceChannel):
        await channel.connect()
        original_voice_channel = channel
    await ensure_playing_hip_hop(channel)

@bot.event
async def on_message(message):
    global waiting_for_selection, waiting_user_id
    if message.author.bot:
        return

    if waiting_for_selection and message.author.id == waiting_user_id:
        if message.content.isdigit():
            choice = int(message.content) - 1
            if choice >= 0:
                waiting_for_selection = False
                await handle_selection(message, choice)
            else:
                await message.channel.send("Invalid choice.")
        else:
            waiting_for_selection = False
            await handle_command(message)
    else:
        await handle_command(message)

async def handle_command(message):
    global waiting_for_selection, waiting_user_id, original_voice_channel
    waiting_for_selection = False

    bot_mention = f'<@{bot.user.id}>'
    bot_role_ids = [role.id for role in (await message.guild.fetch_member(bot.user.id)).roles]
    if bot_mention in message.content or f'<@!{bot.user.id}>' in message.content or any(role_id in [role.id for role in message.role_mentions] for role_id in bot_role_ids):
        content = message.content.split()
        if len(content) > 1 and content[1] == 'play':
            url = content[2] if len(content) > 2 else None
            await enqueue_song(message.channel, url, message)
        elif len(content) > 1 and content[1] == 'search':
            query = ' '.join(content[2:]) if len(content) > 2 else None
            waiting_user_id = message.author.id
            await search(message, query)
        elif len(content) > 1 and content[1] == 'join':
            await join_user_channel(message)
        elif len(content) > 1 and content[1] == 'leave':
            await leave_to_original_channel(message)
        elif len(content) > 1 and content[1] == 'info':
            await show_info(message.channel)
        elif len(content) > 1 and content[1] == 'queue':
            await show_queue(message.channel)

async def join_user_channel(message):
    if message.author.voice and message.author.voice.channel:
        channel = message.author.voice.channel
        voice_client = discord.utils.get(bot.voice_clients, guild=message.guild)
        if voice_client and voice_client.is_connected():
            await voice_client.move_to(channel)
        else:
            await channel.connect()
        await message.channel.send(f"Joined {channel.name}")
    else:
        await message.channel.send("You are not connected to a voice channel.")

async def leave_to_original_channel(message):
    global original_voice_channel
    voice_client = discord.utils.get(bot.voice_clients, guild=message.guild)
    if voice_client and voice_client.is_connected():
        if original_voice_channel and original_voice_channel != voice_client.channel:
            await voice_client.move_to(original_voice_channel)
            await message.channel.send(f"Moved back to {original_voice_channel.name}")
        else:
            await message.channel.send("Already in the original voice channel.")
    else:
        await message.channel.send("I am not connected to a voice channel.")

async def enqueue_song(channel, url, message, title=None):
    global song_queue, hip_hop_playing, song_playing
    try:
        if not title:
            song_info = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            title = song_info.title
        song_queue.append((title, url, message.author.id))
        await channel.send(f'Song "{title}" added to queue. Position: {len(song_queue)}')
        if not song_playing:
            if hip_hop_playing:
                hip_hop_playing = False
                voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)
                if voice_client and voice_client.is_playing():
                    voice_client.stop()
            await play_next_song(channel, message)  # Pass the message for reference
    except Exception as e:
        await channel.send(f"An error occurred: {str(e)}")

async def play_next_song(channel, message=None):
    global song_queue, hip_hop_playing, song_playing, current_song
    if not song_queue:
        await ensure_playing_hip_hop(channel)
        return

    song_title, url, requester_id = song_queue[0]  # Peek at the first item in the queue
    try:
        voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)
        if not voice_client:
            voice_client = await channel.connect()

        if voice_client.is_playing():
            voice_client.stop()

        async with channel.typing():
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(handle_song_end(channel), bot.loop))
        await channel.send(f'Now playing: {song_title}', reference=message)  # Use song_title instead of player.title
        song_playing = True  # Set the song playing flag
        current_song = (song_title, url, requester_id)
        song_queue.pop(0)
    except Exception as e:
        await channel.send(f"An error occurred: {str(e)}", reference=message)

async def handle_selection(message, choice):
    global search_results_cache, song_queue
    try:
        search_results = search_results_cache.get(message.author.id)
        if search_results and 0 <= choice < len(search_results):
            selected = search_results[choice]
            url = selected['url']
            title = selected['title']
            await enqueue_song(message.channel, url, message, title)
        else:
            await message.channel.send("Invalid choice.")
    except IndexError:
        await message.channel.send("Invalid choice.")
    except Exception as e:
        await message.channel.send(f"An error occurred: {str(e)}")

async def handle_song_end(channel):
    global song_queue, song_playing, current_song
    song_playing = False  # Reset the song playing flag
    current_song = None
    if song_queue:
        await play_next_song(channel)
    else:
        await ensure_playing_hip_hop(channel)

async def ensure_playing_hip_hop(channel):
    global song_queue, hip_hop_playing, song_playing
    if not song_queue and not song_playing and not hip_hop_playing:
        hip_hop_playing = True
        await search_and_play_hip_hop(channel)

async def search_and_play_hip_hop(channel):
    try:
        results = await bot.loop.run_in_executor(None, lambda: YTDLSource.ytdl.extract_info(f"ytsearch1:Dance Radio Hits 2024' Dance Music 2024 - Top Hits 2024 Hip Hop, Rap R&B Songs 2024 Best Music 2024", download=False))
        if 'entries' in results:
            hip_hop_url = results['entries'][0]['url']
            await play_hip_hop(channel, hip_hop_url)
    except Exception as e:
        await channel.send(f"An error occurred while searching for hip hop: {str(e)}")

async def play_hip_hop(channel, url):
    global hip_hop_playing
    try:
        voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)
        if not voice_client:
            voice_client = await channel.connect()

        if voice_client.is_playing():
            voice_client.stop()

        async with channel.typing():
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(handle_hip_hop_end(channel), bot.loop))
        await channel.send(f'Now playing: Hip Hop Radio - Hot 108 Jamz')
    except Exception as e:
        hip_hop_playing = False
        await channel.send(f"An error occurred while playing hip hop: {str(e)}")

async def handle_hip_hop_end(channel):
    global hip_hop_playing, song_playing
    hip_hop_playing = False
    if not song_playing and not song_queue:
        await ensure_playing_hip_hop(channel)

async def search(message, query):
    global waiting_for_selection, waiting_user_id, search_results_cache
    try:
        channel = message.channel
        async with channel.typing():
            results = await bot.loop.run_in_executor(None, lambda: YTDLSource.ytdl.extract_info(f"ytsearch5:{query}", download=False))
            if 'entries' not in results:
                await channel.send("No results found.")
                return

            search_results = results['entries']
            response = "\n".join([f"{i+1}. {entry['title']}" for i, entry in enumerate(search_results)])

            search_results_cache[message.author.id] = search_results

            await channel.send(response)
            await channel.send("Please type the number of the video you want to play.")

            waiting_for_selection = True
            waiting_user_id = message.author.id

    except Exception as e:
        await channel.send(f"An error occurred during the search: {str(e)}")

async def show_info(channel):
    info_message = (
        "Commands:\n"
        "@bot.name play <url> - Add a song to the queue and play it.\n"
        "@bot.name search <query> - Search for a song to play.\n"
        "@bot.name join - Make the bot join your voice channel.\n"
        "@bot.name leave - Make the bot leave your voice channel and return to the original channel.\n"
        "@bot.name info - Show this help message.\n"
        "@bot.name queue - Show the current song queue."
    )
    await channel.send(info_message)

async def show_queue(channel):
    global song_queue, song_playing, current_song, hip_hop_playing
    if not song_queue and not song_playing and not hip_hop_playing:
        await channel.send("The queue is currently empty.")
        return

    queue_message = "Current song queue:\n"
    if song_playing or hip_hop_playing:
        if current_song:
            current_playing = f"Currently playing: {current_song[0]} (requested by {await get_user_display_name(current_song[2])})\n"
        else:
            current_playing = "Currently playing: Hip Hop Radio - Hot 108 Jamz (default mix)\n"
        queue_message += current_playing

    for idx, (title, _, requester_id) in enumerate(song_queue):
        requester_display_name = await get_user_display_name(requester_id)
        queue_message += f"{idx+1}. {title} (requested by {requester_display_name})\n"

    await channel.send(queue_message)

async def get_user_display_name(user_id):
    user = await bot.fetch_user(user_id)
    return user.display_name if user else "Unknown user"

bot.run(BOT_TOKEN)
