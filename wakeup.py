import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
import logging
import asyncio
import urllib.parse
import time # Added for debugging timing

# Set up logging for the cog
logger = logging.getLogger('WakeupCog')
logger.setLevel(logging.DEBUG) # Set to DEBUG to capture more info

# --- Configuration ---
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
        # DEBUG: Log the start time immediately upon entering the function
        start_time = time.time()
        logger.debug(f"Wakeup command received from {interaction.user.name} at {start_time}")

        # CRITICAL FIX: The deferral MUST be the first thing to happen.
        # We use a try/except specifically for the deferral.
        try:
            # Attempt the deferral. This is the action that MUST happen within 3 seconds.
            await interaction.response.defer(thinking=True)
            logger.debug(f"Interaction successfully deferred after {time.time() - start_time:.3f} seconds.")
        except discord.errors.NotFound as e:
            # If we hit the 404/Unknown interaction error here, it means we missed the 3-second window.
            # The only way to fix this is to address the lag in the hosting environment (Render).
            logger.error(f"Failed to defer interaction (404/Timeout) for user {interaction.user.name}. Error: {e}")
            
            # Since we can't respond to the user, we exit the function immediately.
            return
        except Exception as e:
            # Catch other potential errors during deferral
            logger.error(f"Unexpected error during deferral for user {interaction.user.name}. Error: {e}")
            return
        
        # --- Continue Execution (Only if Deferral Succeeded) ---

        if not WEBHOOK_SERVER_URL:
            # Use followup.send() because deferral was successful
            await interaction.followup.send("❌ Error: WEBHOOK_SERVER_URL environment variable is not set correctly.")
            return

        # Prepare the target URL and parameters for your webserver
        target_url = f"{WEBHOOK_SERVER_URL}/dynamic-song-trigger"
        
        params = {
            "song": song_name, 
            "user": interaction.user.display_name
        }
        
        try:
            # Use aiohttp for better async performance, which is often faster than requests with to_thread
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                 # Making the asynchronous GET request
                 response = await session.get(
                    target_url,
                    params=params,
                    timeout=10
                 )
                 
                 response_text = await response.text()
                 
            # Use followup.send() since we already called defer()
            if response.status == 200:
                await interaction.followup.send(
                    f"🔊 **Success!** Sent request to Alexa to play: **{song_name}**."
                )
            else:
                error_details = response_text[:200]
                await interaction.followup.send(
                    f"⚠️ **Server Error** (Status: {response.status}): Failed to trigger the command. Check server logs. Details: ```{error_details}```"
                )

        except aiohttp.ClientConnectorError:
            await interaction.followup.send(
                f"❌ **Connection Error!** Could not connect to the internal webhook server at `{WEBHOOK_SERVER_URL}`. Is the server running?"
            )
            logger.error(f"AIOHTTP Connection error to internal webhook.")
        except Exception as e:
            await interaction.followup.send(
                "🤯 **Internal Error.** Something went wrong during the request."
            )
            logger.error(f"Unexpected error during webhook call: {e}")


# --- Setup Function for Bot Extensions ---

async def setup(bot):
    """Required function to load the cog into the bot."""
    await bot.add_cog(WakeupCog(bot))
    logger.info("WakeupCog successfully loaded.")