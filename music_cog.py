import discord
from discord.ext import commands
import yt_dlp
import asyncio

# Suppress harmless errors relating to voice
yt_dlp.utils.bug_reports_message = lambda: ''

# YDL options for fetching stream information (no download)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'default_search': 'auto',
    'extract_flat':
    'True',  # Fast search without detailed metadata for non-first items
}

# FFmpeg options for streaming audio
FFMPEG_OPTIONS = {
    'before_options':
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'  # Tells ffmpeg to not expect video
}


class Song:
    """A simple class to hold song information for the queue."""

    def __init__(self, source, title, url, requester):
        self.source = source
        self.title = title
        self.url = url
        self.requester = requester  # discord.Member object


class MusicCog(commands.Cog):
    """A collection of commands for handling voice connections and music features."""

    def __init__(self, bot):
        self.bot = bot
        # State management for the music bot
        self.is_playing = False
        self.music_queue = []
        self.ydl = yt_dlp.YoutubeDL(YDL_OPTIONS)

    # --- Helper Functions ---

    def get_voice_channel(self, ctx: commands.Context):
        """Returns the voice channel the command author is in, or None."""
        if not ctx.author.voice:
            return None
        return ctx.author.voice.channel

    async def search_yt(self, item):
        """Searches YouTube/links for audio stream data."""
        loop = self.bot.loop or asyncio.get_event_loop()

        # Determine if the item is a URL or a search query
        is_url = item.startswith(('http://', 'https://'))

        try:
            # Run the search synchronously in an executor thread
            data = await loop.run_in_executor(
                None, lambda: self.ydl.extract_info(item, download=False))

            if 'entries' in data:
                # If it's a playlist or a generic search that returned multiple results
                # We often only want the first result for simplicity in a simple play command
                entry = data['entries'][0]
            else:
                # Single video result
                entry = data

            # Extract the actual stream URL and song details
            final_url = entry['url']
            title = entry.get('title', 'Unknown Title')

            return final_url, title
        except Exception:
            return None, "Error processing source/link."

    def play_next(self, ctx):
        """Starts playing the next song in the queue."""
        if self.music_queue:
            self.is_playing = True

            # Get the first Song object from the queue
            current_song = self.music_queue.pop(0)

            # Create an audio source from the stream URL
            source = discord.FFmpegOpusAudio(current_song.source,
                                             **FFMPEG_OPTIONS)

            # Start playing the audio and set a callback for when it finishes
            ctx.voice_client.play(source,
                                  after=lambda e: self.bot.loop.
                                  call_soon_threadsafe(self.play_next, ctx))

            # Send notification (must be done in a separate task as this function is executed in a thread)
            asyncio.run_coroutine_threadsafe(
                ctx.send(
                    f"🎶 Now playing: **{current_song.title}** (Requested by {current_song.requester.display_name})"
                ), self.bot.loop)
        else:
            self.is_playing = False
            # Can disconnect here if queue is empty, but we'll leave it simple for now.

    async def join_voice_channel(self, ctx: commands.Context,
                                 channel: discord.VoiceChannel):
        """Handles joining or moving the bot to a voice channel."""
        if ctx.voice_client is None:
            await channel.connect()
            await ctx.send(f"Connected to voice channel **{channel.name}**!")
        elif ctx.voice_client.channel.id != channel.id:
            await ctx.voice_client.move_to(channel)
            await ctx.send(f"Moved to **{channel.name}**!")
        else:
            await ctx.send("I'm already here! Ready to play some tunes.")

    # --- Commands ---

    @commands.command(name="join", aliases=["j"])
    async def join_command(self, ctx: commands.Context):
        """Makes the bot join the voice channel you are currently in."""
        channel = self.get_voice_channel(ctx)
        if not channel:
            return await ctx.send(
                "You need to be in a voice channel for the bot to join!")

        await self.join_voice_channel(ctx, channel)

    @commands.command(name="leave", aliases=["l", "disconnect"])
    async def leave_command(self, ctx: commands.Context):
        """Disconnects the bot from the current voice channel, stopping playback and clearing the queue."""
        if ctx.voice_client:
            # Clear the queue and stop playing
            self.music_queue.clear()
            self.is_playing = False

            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            await ctx.voice_client.disconnect()
            await ctx.send("Disconnected and queue cleared. Bye! 👋")
        else:
            await ctx.send("I am not currently connected to any voice channel."
                           )

    @commands.command(name="play", aliases=["p"])
    async def play_command(self, ctx: commands.Context, *, search_query: str):
        """Searches for a song/link and adds it to the queue. Automatically joins if not connected."""
        await ctx.defer(
        )  # Defer the response for long-running network operations

        # 1. Check/Join Voice Channel
        channel = self.get_voice_channel(ctx)
        if not channel:
            return await ctx.send(
                "You need to be in a voice channel to request music!")

        if ctx.voice_client is None:
            await self.join_voice_channel(ctx, channel)
        elif ctx.voice_client.channel.id != channel.id:
            await self.join_voice_channel(ctx, channel)

        # Ensure we have a voice client after connecting/joining
        if not ctx.voice_client:
            # If connect failed for some reason
            return await ctx.send(
                "Could not connect to the voice channel. Check bot permissions."
            )

        # 2. Search and Enqueue Song
        stream_url, title = await self.search_yt(search_query)

        if stream_url is None:
            return await ctx.send(
                f"Could not find or process audio for: `{search_query}`")

        new_song = Song(stream_url, title, search_query, ctx.author)
        self.music_queue.append(new_song)

        if not ctx.voice_client.is_playing() and not self.is_playing:
            # If the bot is idle, start playing immediately
            self.play_next(ctx)
        else:
            # Otherwise, add to the queue
            await ctx.send(f"✅ Added to queue: **{title}**")

    @commands.command(name="queue", aliases=["q", "list"])
    async def queue_command(self, ctx: commands.Context):
        """Displays the current song queue."""
        if not self.music_queue:
            return await ctx.send("The music queue is currently empty!")

        # Create a nicely formatted list
        queue_list = "\n".join([
            f"**{i+1}.** {song.title} (Requested by {song.requester.display_name})"
            for i, song in enumerate(self.music_queue)
        ])

        # Use an Embed for a cleaner look
        embed = discord.Embed(title="🎶 Current Music Queue 🎶",
                              description=queue_list,
                              color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(name="skip", aliases=["s"])
    async def skip_command(self, ctx: commands.Context):
        """Skips the currently playing song."""
        if ctx.voice_client is None or not ctx.voice_client.is_playing():
            return await ctx.send("I am not currently playing any music.")

        # Stop the current playback, which triggers the 'after' callback, calling play_next()
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped current song.")

    @commands.command(name="stop")
    async def stop_command(self, ctx: commands.Context):
        """Stops the music and clears the entire queue."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            self.music_queue.clear()
            self.is_playing = False
            await ctx.send("⏹️ Music stopped and queue cleared.")
        elif self.music_queue:
            self.music_queue.clear()
            await ctx.send("Queue cleared, but no music was playing.")
        else:
            await ctx.send("No music is currently playing or queued.")


# Setup function is mandatory for Cogs
async def setup(bot: commands.Bot):
    """Loads the MusicCog into the bot."""
    await bot.add_cog(MusicCog(bot))
