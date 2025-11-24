import discord
from discord.ext import commands
from discord import app_commands
import os
import requests
import asyncio
import logging

# Set up logging for better visibility
logger = logging.getLogger('WakeupCog')
logger.setLevel(logging.INFO)

# --- Configuration (Load from environment) ---
WEBHOOK_SERVER_URL = os.getenv("WEBHOOK_SERVER_URL")

class WakeupCog(commands.Cog):
    """
    A Cog that handles the /wakeup slash command by sending a request 
    to the external Python Webhook Server.
    """
    def __init__(self, bot: commands.Bot):
        # The bot object is passed to the cog upon initialization
        self.bot = bot

    @app_commands.command(name="wakeup", description="Play a song via Alexa using the dynamic Voice Monkey API.")
    @app_commands.describe(
        song_name="The song or playlist you want Alexa to play (e.g., 'Never Gonna Give You Up')."
    )
    async def wakeup_slash(self, interaction: discord.Interaction, song_name: str):
        # Acknowledge the interaction immediately to prevent the 3-second timeout
        try:
            await interaction.response.defer(ephemeral=False, thinking=True)
        except discord.errors.NotFound:
            logger.error("Error: Could not defer interaction.")
            return

        # 1. Prepare data for the proxy webhook call
        user_name = interaction.user.display_name
        
        # 2. Construct the full URL for the dynamic song trigger
        if not WEBHOOK_SERVER_URL:
            await interaction.followup.send(
                "Error: The bot admin needs to configure the WEBHOOK_SERVER_URL environment variable.", 
                ephemeral=True
            )
            return
            
        full_webhook_url = f"{WEBHOOK_SERVER_URL}/dynamic-song-trigger"
        params = {
            "song": song_name,
            "user": user_name
        }

        logger.info(f"User {user_name} triggering song: {song_name}. Calling webhook: {full_webhook_url}")

        # 3. Call the external webhook server
        try:
            # Use asyncio.to_thread for synchronous requests call in an async function
            response = await asyncio.to_thread(
                requests.get,
                full_webhook_url,
                params=params,
                timeout=10 # 10 seconds timeout for the entire external call
            )

            if response.status_code == 200:
                # Success response from your webhook server
                await interaction.followup.send(
                    f"🔊 Success! Alexa command sent for: **{song_name}**.",
                    ephemeral=False
                )
            else:
                # Error from your webhook server (e.g., 500 or 503)
                error_message = f"Proxy Server Error ({response.status_code}): {response.text}"
                await interaction.followup.send(
                    f"❌ Failed to trigger Alexa via webhook. Details: ```{error_message}```",
                    ephemeral=True
                )
                logger.error(f"Webhook failed with status {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            # Network or timeout error when calling the webhook
            await interaction.followup.send(
                f"❌ Failed to connect to the Alexa proxy server. Please check the server status and URL configuration.",
                ephemeral=True
            )
            logger.error(f"Request Exception: {e}")

# This is the mandatory setup function used by the discord.ext.commands framework
async def setup(bot):
    """Adds the WakeupCog to the bot."""
    await bot.add_cog(WakeupCog(bot))
    logger.info("WakeupCog successfully loaded and ready to sync commands.")

# Optional: Add a teardown function
async def teardown(bot):
    """Removes the WakeupCog from the bot."""
    await bot.remove_cog("WakeupCog")
    logger.info("WakeupCog successfully unloaded.")