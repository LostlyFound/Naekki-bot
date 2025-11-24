import os
import threading
import asyncio
from aiohttp import web

# --- Handlers ---

# This is the function that runs when UptimeRobot hits your public URL.
async def keep_awake_handler(request):
    """Responds with a simple status to keep the Render service awake."""
    return web.Response(text="Bot is running and awake.", status=200)

# --- Server Logic ---

def start_server():
    """Starts the aiohttp web server in its own thread."""
    # Render provides the port number via the PORT environment variable
    try:
        port = int(os.environ.get('PORT', 8080))
    except (TypeError, ValueError):
        port = 8080 # Fallback port
        
    print(f"Starting web server on port {port}...")

    # Set up the aiohttp application
    app = web.Application()
    app.router.add_get('/', keep_awake_handler)
    
    # Need to create and run the event loop in this new thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Configure and start the server site
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # Start serving and keep the loop running indefinitely
    loop.run_until_complete(site.start())
    loop.run_forever()

# Main entry point for the keep-alive feature
def keep_alive():
    """Launches the web server in a separate daemon thread."""
    # Daemon thread ensures the main bot process can still exit if needed
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    print("Keep-alive thread started.")

if __name__ == '__main__':
    # This block is for testing the webserver locally if needed
    keep_alive()