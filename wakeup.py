import discord
from discord import app_commands
import os
import requests
import asyncio # Keep asyncio for future use

# --- Firebase and LLM Configuration (omitted for brevity, assume initialized) ---

# Load bot secrets from environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_SERVER_URL = os.getenv("WEBHOOK_SERVER_URL") # Base URL of your Python server (e.g., https://your-render-app.onrender.com)

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Initialize command tree
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')

@client.tree.command(name="wakeup", description="Play a song via Alexa using the dynamic Voice Monkey API.")
@app_commands.describe(
    song_name="The song or playlist you want Alexa to play (e.g., 'Never Gonna Give You Up')."
)
async def wakeup_slash(interaction: discord.Interaction, song_name: str):
    # =================================================================
    # CRITICAL FIX: DEFER IMMEDIATELY
    # Acknowledge the interaction within 3 seconds to prevent the timeout error.
    # We use ephemeral=True so the "Bot is thinking..." message is private.
    # =================================================================
    try:
        await interaction.response.defer(ephemeral=False, thinking=True)
    except discord.errors.NotFound:
        # If somehow we still get a timeout here, log and exit.
        print("Error: Could not defer interaction. Token expired prematurely.")
        return

    # 1. Prepare data for the proxy webhook call
    # We get the user's display name for a friendly message
    user_name = interaction.user.display_name
    
    # 2. Construct the full URL for the dynamic song trigger
    # This URL targets the new route in your webhook_server.py
    # The song name and user name are passed as query parameters
    if not WEBHOOK_SERVER_URL:
        await interaction.followup.send(
            "Error: WEBHOOK_SERVER_URL is not configured.", 
            ephemeral=True
        )
        return
        
    full_webhook_url = f"{WEBHOOK_SERVER_URL}/dynamic-song-trigger"
    params = {
        "song": song_name,
        "user": user_name
    }

    print(f"Attempting to trigger webhook: {full_webhook_url} with song: {song_name}")

    # 3. Call the external webhook server
    try:
        # Use a short timeout for the webhook call
        response = await asyncio.to_thread(
            requests.get,
            full_webhook_url,
            params=params,
            timeout=10 # Give it 10 seconds to hit your server and Voice Monkey
        )

        if response.status_code == 200:
            # Success response from your webhook server
            response_text = response.text 
            
            # Send the final response using followup.send since we deferred earlier
            await interaction.followup.send(
                f"🔊 Success! Alexa command sent for: **{song_name}**.",
                ephemeral=False
            )
        else:
            # Error from your webhook server (e.g., 500 or 503)
            error_message = f"Proxy Server Error ({response.status_code}): {response.text}"
            await interaction.followup.send(
                f"❌ Failed to trigger Alexa via webhook. Details: {error_message}",
                ephemeral=True
            )
            print(f"Webhook failed with status {response.status_code}: {response.text}")

    except requests.exceptions.RequestException as e:
        # Network or timeout error when calling the webhook
        error_message = f"Network error when connecting to webhook: {e}"
        await interaction.followup.send(
            f"❌ Failed to connect to the Alexa proxy server. Please check the server status.",
            ephemeral=True
        )
        print(f"Request Exception: {e}")

# --- Placeholder Client Run (omitted for brevity, assume running) ---
# client.run(DISCORD_TOKEN)