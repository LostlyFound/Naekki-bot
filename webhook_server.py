from flask import Flask, request
import os
import requests
import urllib.parse
import json

app = Flask(__name__)

# Load secrets from environment variables
WEBHOOK_AUTH_TOKEN = os.getenv("WEBHOOK_AUTH_TOKEN")
DEFAULT_CHANNEL_ID = os.getenv("DEFAULT_CHANNEL_ID")
VOICE_MONKEY_BASE_URL = os.getenv("VOICE_MONKEY_BASE_URL") # << NEW SECRET

# =========================================================================
# NEW DYNAMIC SONG ROUTE (The Free Solution)
# =========================================================================
@app.route("/dynamic-song-trigger", methods=["GET"])
def dynamic_song_trigger():
    """
    Receives the song name from the Discord bot, constructs the exact 
    Voice Monkey command, and sends it directly.
    """
    
    # Extract data from the URL query parameters
    song_name = request.args.get("song", "Default Alarm")
    user_name = request.args.get("user", "Someone")
    
    # 1. Check for the Voice Monkey Base URL
    if not VOICE_MONKEY_BASE_URL:
        print("ERROR: VOICE_MONKEY_BASE_URL not set!")
        return "Internal Configuration Error: Voice Monkey URL Missing", 500

    # 2. Construct the Alexa command string (e.g., "play Never Gonna Give You Up on Spotify")
    # You can change "Spotify" to your preferred music service.
    alexa_command = f"play {song_name} on Spotify" 
    
    # 3. URL-encode the command string (absolutely necessary!)
    encoded_command = urllib.parse.quote_plus(alexa_command)

    # 4. Construct the FINAL Voice Monkey URL
    # We append the custom command parameter directly to the base URL
    final_vm_url = f"{VOICE_MONKEY_BASE_URL}&command={encoded_command}"
    
    print(f"Sending FINAL VM URL: {final_vm_url}")
    
    try:
        # 5. Send the request to Voice Monkey
        response = requests.get(final_vm_url, timeout=5)
        
        if response.status_code == 200:
            return f"Requested **{song_name}** for {user_name}.", 200
        else:
            print(f"Voice Monkey API failed: {response.status_code}, {response.text}")
            return f"Voice Monkey API Error: Status {response.status_code}", 503
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Voice Monkey: {e}")
        return "Failed to connect to Voice Monkey.", 503


# =========================================================================
# EXISTING WEBHOOK ROUTE (Keep your old Alexa/IFTTT trigger for stability)
# =========================================================================
@app.route("/alexa-trigger", methods=["POST"])
def alexa_trigger():
    """
    Receives triggers from an external service (like Voice Monkey)
    to make the bot speak in Discord.
    """
    
    data = request.get_json(silent=True)
    
    if not data or not data.get("auth_token") == WEBHOOK_AUTH_TOKEN:
        return {"status": "Unauthorized"}, 401

    message_content = data.get("message", "A custom command was triggered!")
    
    # This part assumes you have access to your Discord bot's methods 
    # to send a message. Since the web server runs separately, this is a placeholder.
    # In a real setup, this would use a dedicated message queue or Discord API call.
    print(f"Received message to send to Discord: {message_content}")
    
    # Placeholder response to confirm receipt
    return {"status": "Message received, attempting to send to Discord"}, 200


# =========================================================================
# KEEPALIVE ROUTE
# =========================================================================
@app.route("/", methods=["GET"])
def keep_alive():
    return "AI Chat Bot Webhook Server Running", 200


if __name__ == "__main__":
    # Ensure this runs the server in the main bot process if required,
    # or runs separately if you have a multi-process setup.
    # For Render/single-process bots, you might launch this from main.py
    # using threading or run it in a separate service.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)