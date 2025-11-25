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
    # This is the exact phrase Alexa needs to hear to play music.
    alexa_command = f"play {song_name} on Spotify"
    
    # 2. URL-encode the command (CRITICAL step for special characters like spaces)
    encoded_command = urllib.parse.quote_plus(alexa_command)
    
    # 3. Construct final Voice Monkey URL
    # We append the custom command parameter directly to the base URL
    # NOTE: We use '&command=' assuming the BASE_URL already contains the initial '?' for query start.
    final_vm_url = f"{VOICE_MONKEY_BASE_URL}&command={encoded_command}"
    
    print(f"Triggering Voice Monkey: {final_vm_url}")

    try:
        # Use aiohttp for asynchronous request handling
        async with aiohttp.ClientSession() as session:
            # Send the request to Voice Monkey
            async with session.get(final_vm_url) as response:
                if response.status == 200:
                    # Check for "success" in the response text (Voice Monkey often returns JSON)
                    response_text = await response.text()
                    if "success" in response_text.lower():
                        print(f"Voice Monkey success response: {response_text}")
                        return web.Response(text=f"Successfully requested '{song_name}' for {user_name}.", status=200)
                    else:
                         # Voice Monkey responded 200, but execution failed (e.g., command syntax error)
                        print(f"Voice Monkey 200 but execution likely failed. Response: {response_text}")
                        return web.Response(text=f"VM 200 OK, but command execution failed. Alexa may need a moment or the command syntax is wrong.", status=500)
                else:
                    error_text = await response.text()
                    print(f"Voice Monkey API returned non-200 status: {response.status}. Response: {error_text}")
                    return web.Response(text=f"Voice Monkey Error: {error_text}", status=502)
    except Exception as e:
        print(f"Network error during Voice Monkey call: {e}")
        return web.Response(text=f"Internal Error during network call: {str(e)}", status=500)

# --- Server Logic (Unchanged) ---

def start_server():
    """Starts the aiohttp web server in its own thread."""
    try:
        port = int(os.environ.get('PORT', 8080))
    except (TypeError, ValueError):
        port = 8080 
        
    print(f"Starting web server on port {port}...")

    app = web.Application()
    app.router.add_get('/', keep_awake_handler)
    app.router.add_get('/dynamic-song-trigger', dynamic_song_trigger)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    loop.run_until_complete(site.start())
    loop.run_forever()

def keep_alive():
    """Launches the web server in a separate daemon thread."""
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

if __name__ == "__main__":
    keep_alive()