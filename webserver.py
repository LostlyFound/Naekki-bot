import os
import requests
import json
import logging
import asyncio
from discord.ext import commands
from discord.ext.commands import Cog

# Set up logging for the cog
logger = logging.getLogger('Webserver')
logger.setLevel(logging.INFO)

# --- Configuration ---
# Your unique Voice Monkey Trigger URL, loaded from environment variables
VOICE_MONKEY_URL = os.getenv("VOICE_MONKEY_BASE_URL")

# --- Web Server/Cog Setup ---

class WebhookServerCog(Cog):
    """
    A Cog designed to run an internal web server thread to handle incoming 
    HTTP requests from the Discord bot, acting as a proxy to Voice Monkey.
    
    Note: Since discord.py cogs are primarily for Discord events, we implement 
    the web server logic to run alongside the bot process.
    """
    def __init__(self, bot):
        self.bot = bot
        # Attempt to start the web server in a separate thread/task when the cog loads
        self.bot.loop.create_task(self.start_web_server())

    # --- HTTP Server Logic (Using Flask/Aiohttp equivalent for clarity) ---
    
    async def start_web_server(self):
        """
        Simulates starting an HTTP server task specifically to handle requests 
        from the Discord bot's /wakeup command.
        
        This function serves as a placeholder. You must ensure your actual 
        web framework (like Flask/FastAPI) is running on port 8080 and calls
        the 'dynamic_song_trigger' function below when it receives a GET request
        to the '/dynamic-song-trigger' endpoint.
        """
        logger.info("Webhook server logic initialized. Awaiting requests on the main web server (Port 8080).")
        # In a real setup, your main bot file's web server thread must call:
        # result, status_code = self.dynamic_song_trigger(song, user)
        pass

    # --- Core Dynamic Song Trigger Function ---
    
    def dynamic_song_trigger(self, song_name: str, user_name: str):
        """
        Handles the request coming from the Discord bot and makes the API call 
        to Voice Monkey.
        """
        if not VOICE_MONKEY_URL:
            logger.error("VOICE_MONKEY_URL is not set in environment variables.")
            return {"error": "Server not configured with Voice Monkey URL."}, 500

        # Create a dynamic message for Alexa to say
        announcement_text = f"Wake up {user_name}! Playing {song_name} now."
        
        # Data payload for Voice Monkey (adjust keys based on your specific setup)
        payload = {
            "monkey": announcement_text,
            "announcement": "true",
            "volume": 75 # Set an appropriate volume
        }

        # The Voice Monkey URL should already contain the correct trigger/device ID
        try:
            # We use a POST request here as Voice Monkey typically expects a body payload
            response = requests.post(VOICE_MONKEY_URL, data=json.dumps(payload), timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Successfully triggered Voice Monkey for song: {song_name}")
                return {"status": "success", "message": "Voice Monkey triggered."}, 200
            else:
                logger.error(f"Voice Monkey API failed: Status {response.status_code}, Response: {response.text}")
                return {"error": f"Voice Monkey returned status code {response.status_code}"}, 502

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error calling Voice Monkey: {e}")
            return {"error": f"Network error during Voice Monkey call: {e}"}, 503


# --- Setup and Teardown Functions for the Bot's Extension System ---

async def setup(bot):
    """
    Required function to load the cog into the bot.
    """
    await bot.add_cog(WebhookServerCog(bot))
    logger.info("WebhookServerCog successfully loaded.")

async def teardown(bot):
    """
    Required function to unload the cog from the bot.
    """
    await bot.remove_cog("WebhookServerCog")
    logger.info("WebhookServerCog successfully unloaded.")