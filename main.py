import os
import discord
from discord.ext import commands
from webserver import keep_alive 
from google import genai
from google.genai import types
import asyncio

# --- Configuration ---
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("FATAL ERROR: Please set both DISCORD_TOKEN and GEMINI_API_KEY environment variables.")
    exit()

# Initialize Gemini
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    exit()

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True 
intents.dm_messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Conversation History for AI
conversation_histories = {} 
MODEL = 'gemini-2.5-flash-preview-09-2025'
SYSTEM_INSTRUCTION = (
    "You are Naekki, a friendly, supportive, and slightly playful relationship-bot. "
    "Keep responses concise and fun."
)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    
    # --- Load Cogs ---
    # Load all your feature cogs here
    initial_extensions = ['fun', 'ai_chat', 'couples', 'wakeup','webserver','webhook_server']
    
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            print(f"Successfully loaded {extension}.")
        except Exception as e:
            print(f"Failed to load {extension}: {e}")

    # --- Sync Commands ---
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} application commands globally.")
    except Exception as e:
        print(f"Failed to sync application commands: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # ... (Keep your existing AI Chat logic here if you haven't moved it to ai_chat.py) ...
    # If you are using the 'ai_chat' cog, you don't need logic here, just:
    await bot.process_commands(message)

# --- Startup ---
keep_alive() # Starts the webserver defined in webserver.py

if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)