import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
import logging
import asyncio
import urllib.parse

# Set up logging for the cog
logger = logging.getLogger('WakeupCog')
logger.setLevel(logging.INFO)

# --- Configuration ---
# Your bot's public URL (e.g., https://naekii-bot.onrender.com) 
# This is where the webhook server is running.
WEBHOOK_SERVER_URL = os.getenv("WEBHOOK_SERVER_URL") 

class WakeupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("WakeupCog initialized.")

    @app_commands.command(
        name="wakeup", 
        description="Trigger an alarm or song using Voice Monkey via the internal webhook server."
    )
    @app_commands.describe(
        song_name="The name of the song or alarm you want Alexa to play (e.g., 'Never Gonna Give You Up')."
    )
    async def wakeup(self, interaction: discord.Interaction, song_name: str):
        
        # CRITICAL FIX: Defer the response immediately to beat the 3-second timeout.
        try:
            await interaction.response.defer(thinking=True)
        except Exception as e:
            # If deferral still fails, log the error but don't proceed.
            logger.error(f"Failed to defer interaction: {e}")
            return


        if not WEBHOOK_SERVER_URL:
            await interaction.followup.send("❌ Error: WEBHOOK_SERVER_URL environment variable is not set correctly.")
            return

        # Prepare the target URL and parameters for your webserver
        target_url = f"{WEBHOOK_SERVER_URL}/dynamic-song-trigger"
        
        # Prepare parameters for the webserver (which will then talk to Voice Monkey)
        params = {
            "song": song_name, 
            "user": interaction.user.display_name
        }
        
        # The webserver expects a GET request with query parameters
        try:
            # Use asyncio.to_thread for synchronous requests call in an async function
            response = await asyncio.to_thread(
                requests.get,
                target_url,
                params=params,
                timeout=10
            )

            # Use followup.send() since we already called defer()
            if response.status_code == 200:
                await interaction.followup.send(
                    f"🔊 **Success!** Sent request to Alexa to play: **{song_name}**."
                )
            else:
                error_details = response.text[:200]
                await interaction.followup.send(
                    f"⚠️ **Server Error** (Status: {response.status_code}): Failed to trigger the command. Check server logs. Details: ```{error_details}```"
                )

        except requests.exceptions.RequestException as e:
            await interaction.followup.send(
                f"❌ **Connection Error!** Could not connect to the internal webhook server at `{WEBHOOK_SERVER_URL}`. Error: `{e}`"
            )
            logger.error(f"Connection error to internal webhook: {e}")


# --- Setup Function for Bot Extensions ---

async def setup(bot):
    """Required function to load the cog into the bot."""
    await bot.add_cog(WakeupCog(bot))
    logger.info("WakeupCog successfully loaded.")