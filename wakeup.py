import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
import logging
import asyncio

logger = logging.getLogger('WakeupCog')
logger.setLevel(logging.INFO)

# This should be YOUR Render URL (e.g., https://naekki-bot.onrender.com)
WEBHOOK_SERVER_URL = os.getenv("WEBHOOK_SERVER_URL") 

class WakeupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="wakeup", description="Play a song via Alexa using Voice Monkey.")
    @app_commands.describe(song_name="The song to play (e.g., 'Never Gonna Give You Up').")
    async def wakeup(self, interaction: discord.Interaction, song_name: str):
        # 1. Defer immediately to prevent timeout
        await interaction.response.defer(thinking=True)

        if not WEBHOOK_SERVER_URL:
            await interaction.followup.send("❌ Error: WEBHOOK_SERVER_URL not set.")
            return

        target_url = f"{WEBHOOK_SERVER_URL}/dynamic-song-trigger"
        params = {"song": song_name, "user": interaction.user.display_name}

        try:
            # Call our own webserver to handle the logic
            response = await asyncio.to_thread(requests.get, target_url, params=params, timeout=10)
            
            if response.status_code == 200:
                await interaction.followup.send(f"🔊 Sent request to Alexa: **{song_name}**")
            else:
                await interaction.followup.send(f"⚠️ Server Error: {response.text}")

        except Exception as e:
            await interaction.followup.send(f"❌ Connection Failed: {e}")

async def setup(bot):
    await bot.add_cog(WakeupCog(bot))