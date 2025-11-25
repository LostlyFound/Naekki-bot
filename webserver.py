import os
import threading
import asyncio
import urllib.parse
import aiohttp
from aiohttp import web

# --- Configuration ---
# Base URL for Voice Monkey API (Set this in your Environment Variables!)
# Example Format: https://api.voicemonkey.io/trigger?token=...&secret=...&monkey=...
VOICE_MONKEY_BASE_URL = os.getenv("VOICE_MONKEY_BASE_URL")

# --- Handlers ---

async def keep_awake_handler(request):
    """Responds with a simple status to keep the Render service awake."""
    return web.Response(text="Bot is running and awake.", status=200)

async def dynamic_song_trigger(request):
    """
    Handles the request from the Discord bot to play a specific song via Voice Monkey.
    Expects query parameters: ?song=SongName&user=UserName
    """
    song_name = request.query.get("song", "Default Alarm")
    user_name = request.query.get("user", "Someone")

    if not VOICE_MONKEY_BASE_URL:
        print("ERROR: VOICE_MONKEY_BASE_URL not configured.")
        return web.Response(text="Error: VOICE_MONKEY_BASE_URL not configured.", status=500)

    # 1. Construct the Alexa command
    # NOTE: We use Spotify here, but you can change it to "Amazon Music" or another service.
    alexa_command = f"play {song_name} on Spotify"
    
    # 2. URL-encode the command (CRITICAL step for special characters)
    encoded_command = urllib.parse.quote_plus(alexa_command)
    
    # 3. Construct final Voice Monkey URL
    # We append the custom command parameter directly to the base URL
    final_vm_url = f"{VOICE_MONKEY_BASE_URL}&command={encoded_command}"
    
    print(f"Triggering Voice Monkey: {final_vm_url}")

    try:
        # Use aiohttp for asynchronous request handling
        async with aiohttp.ClientSession() as session:
            # Send the request to Voice Monkey
            async with session.get(final_vm_url) as response:
                if response.status == 200:
                    return web.Response(text=f"Successfully requested '{song_name}' for {user_name}.", status=200)
                else:
                    error_text = await response.text()
                    print(f"Voice Monkey API returned non-200 status: {response.status}. Response: {error_text}")
                    return web.Response(text=f"Voice Monkey Error: {error_text}", status=502)
    except Exception as e:
        print(f"Network error during Voice Monkey call: {e}")
        return web.Response(text=f"Internal Error during network call: {str(e)}", status=500)

# --- Server Logic ---

def start_server():
    """Starts the aiohttp web server in its own thread."""
    # Render provides the port number via the PORT environment variable
    try:
        # Ensure we read the port defined by the hosting environment
        port = int(os.environ.get('PORT', 8080))
    except (TypeError, ValueError):
        port = 8080 
        
    print(f"Starting web server on port {port}...")

    app = web.Application()
    # 1. Route for UptimeRobot (Keep Alive)
    app.router.add_get('/', keep_awake_handler)
    # 2. Route for Wakeup Command (Alexa Trigger)
    app.router.add_get('/dynamic-song-trigger', dynamic_song_trigger)
    
    # Create a new event loop for this thread to manage the server asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # Start serving
    loop.run_until_complete(site.start())
    loop.run_forever()

# --- THE ESSENTIAL FUNCTION FOR MAIN.PY ---
def keep_alive():
    """Launches the web server in a separate daemon thread."""
    # This function is what main.py imports and executes.
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

if __name__ == "__main__":
    # If you run webserver.py directly, it starts the server.
    keep_alive()