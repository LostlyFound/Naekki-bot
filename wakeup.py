import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import asyncio
import urllib.parse # Added for URL encoding

class Wakeup(commands.Cog):
    """A Cog for the custom Wakeup command integrated with a Webhook/IFTTT."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # NOTE: This is now the URL of the bot's OWN public server endpoint!
        # Render Public URL is stored in an env variable named "RENDER_EXTERNAL_URL"
        self.base_url = os.getenv("RENDER_EXTERNAL_URL")
        self.allowed_users = self._load_allowed_users()
        # The internal endpoint that processes the request
        self.proxy_endpoint = "/dynamic-song-trigger"
        
    def _load_allowed_users(self):
        # ... (unchanged)
        user_ids_str = os.getenv("ALLOWED_USER_IDS")
        if not user_ids_str:
            print("WARNING: ALLOWED_USER_IDS not set. Wakeup command will not work.")
            return []
        
        try:
            return [int(uid.strip()) for uid in user_ids_str.split(',')]
        except ValueError:
            print("ERROR: ALLOWED_USER_IDS contains non-integer values. Please check the format.")
            return []

    async def _trigger_alexa_webhook(self, user_name, song=None):
        """Sends the request to the bot's own internal proxy server."""
        
        if not self.base_url:
            return "❌ **Configuration Error:** The `RENDER_EXTERNAL_URL` secret is missing. I can't find my own server!"
        
        # 1. URL-encode the song name (required for safe transmission)
        encoded_song = urllib.parse.quote_plus(song or "Default Alarm")
        
        # 2. Construct the full URL to the proxy endpoint
        full_url = f"{self.base_url}{self.proxy_endpoint}?song={encoded_song}&user={urllib.parse.quote_plus(user_name)}"
        
        print(f"Sending request to internal proxy: {full_url}")

        try:
            async with aiohttp.ClientSession() as session:
                # We send a GET request as a simple trigger
                async with session.get(full_url, timeout=10) as response:
                    
                    if response.status == 200:
                        # The internal server will return a success message
                        success_message = await response.text()
                        return f"🔔 **WAKEUP SIGNAL SENT!**\n> {success_message}"
                    else:
                        error_text = await response.text()
                        print(f"Internal Proxy Failure: Status {response.status}, Response: {error_text}")
                        return f"⚠️ **Proxy Error:** My internal server failed to process the request (Status: {response.status})."
        except asyncio.TimeoutError:
            return "⏱️ **Timeout Error:** My server took too long to talk to Voice Monkey."
        except Exception as e:
            print(f"General Proxy Error: {e}")
            return "🚫 **Connection Error:** Something went wrong reaching my own server."

    # --- SLASH COMMAND and PREFIX COMMAND are UNCHANGED (they just call _trigger_alexa_webhook) ---
    @app_commands.command(name='wakeup', description='Sends a signal to your linked Alexa device to wake you up.')
    @app_commands.describe(song='(Optional) A specific song/playlist to play.')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def wakeup_slash(self, interaction: discord.Interaction, song: str = None):
        # Authorization check
        if interaction.user.id not in self.allowed_users:
             await interaction.response.send_message("❌ **Permission Denied:** You are not authorized to use this command.", ephemeral=True)
             return

        await interaction.response.defer()
        
        user_name = interaction.user.display_name
        response_text = await self._trigger_alexa_webhook(user_name, song)
        
        await interaction.followup.send(response_text)

    @commands.command(name='wakeup', help='Sends a signal to your linked Alexa device to wake you up.')
    async def wakeup_prefix(self, ctx: commands.Context, *, song: str = None):
        # ... (Authorization check and execution is the same)
        if ctx.author.id not in self.allowed_users:
             await ctx.send("❌ **Permission Denied:** You are not authorized to use this command.")
             return

        async with ctx.typing():
            user_name = ctx.author.display_name
            response_text = await self._trigger_alexa_webhook(user_name, song)
            await ctx.send(response_text)

async def setup(bot: commands.Cog):
    await bot.add_cog(Wakeup(bot))