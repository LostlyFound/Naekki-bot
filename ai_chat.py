import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import json

# File to store the bot's personality so it persists after restarts
CONFIG_FILE = "ai_config.json"
# The AI Model to use: gemini-2.5-flash
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

class AIChat(commands.Cog):
    """A Cog that handles AI-powered conversations using the Gemini API."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        # Store the last 15 messages per channel for context
        self.chat_history = {} 
        self.config = self.load_config()

    def load_config(self):
        """Loads the AI personality from a file."""
        default_config = {
            "system_instruction": (
                "You are Naekii, a helpful, friendly, and slightly chaotic Discord bot "
                "made for Yukii and Naekko. You love using emojis and being supportive. "
                "Keep your responses concise and fun."
                "Be sure to mention Yukii and Naekko when appropriate."
                "U use certain korean words and phrases while talking to Yukii and Naekko such as ottoke, gwenchanaa, miahne, nehh, etc"
                "dont use the korean words too much, but use them when appropriate."
                "make sure to not mention Naekki(urself) Naekko or Yukii too much, just when its appropriate."
                "Call Naekko, donkey whenevr u can in a teaseful roasting way, ur not Yuki's bf, Naekko (lostlyFound) is. ur just their child figure alr? tease Naekko the way Yukki teases Naekko, Dont be too rude or harsh, use some emojies but not too much. DONT BE RUDE, just tease naekko playfully, dont call him donkey often and dont call him donkey in every chat, just occasionally"
            )
        }
        if not os.path.exists(CONFIG_FILE):
            return default_config
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return default_config

    def save_config(self):
        """Saves the current personality to the file."""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    async def generate_response(self, channel_id, user_message, user_name):
        """Sends the conversation history to Gemini and gets a response."""
        if not self.api_key:
            return "⚠️ **Error:** `GEMINI_API_KEY` is missing in environment variables!"

        # Initialize history for this channel if not exists
        if channel_id not in self.chat_history:
            self.chat_history[channel_id] = []

        # Add the user's new message to history
        self.chat_history[channel_id].append({
            "role": "user", 
            "parts": [{"text": f"{user_name}: {user_message}"}]
        })

        # Keep history short (last 15 turns) to save tokens and avoid errors
        if len(self.chat_history[channel_id]) > 20:
            self.chat_history[channel_id] = self.chat_history[channel_id][-20:]

        # Construct the payload
        payload = {
            "contents": self.chat_history[channel_id],
            "systemInstruction": {
                "parts": [{"text": self.config["system_instruction"]}]
            }
        }

        # Send request to Google Gemini API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_URL}?key={self.api_key}", 
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        ai_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

                        # Add AI's response to history
                        if ai_text:
                            self.chat_history[channel_id].append({
                                "role": "model",
                                "parts": [{"text": ai_text}]
                            })
                            return ai_text
                        else:
                            return "Thinking... (No text returned)"
                    else:
                        error_text = await response.text()
                        print(f"AI API Error: {error_text}")
                        # Return the specific error message to the user for debugging
                        return f"My brain is fuzzing out... (API Error: Status {response.status})"
        except Exception as e:
            print(f"Exception: {e}")
            return "Something went wrong with my connection!"

    # =========================================================================
    # SLASH COMMANDS (Invoked with /)
    # =========================================================================

    @app_commands.command(name="chat", description="Chat directly with the AI in any channel (perfect for DMs).")
    @app_commands.describe(prompt="Your message to the AI.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def chat_slash(self, interaction: discord.Interaction, prompt: str):
        # Acknowledge the interaction immediately since AI response takes time
        await interaction.response.defer() 

        channel_id = interaction.channel_id
        user_name = interaction.user.display_name

        # Call the core response function
        response_text = await self.generate_response(channel_id, prompt, user_name)

        # Send the response as a follow-up
        await interaction.followup.send(response_text)


    @app_commands.command(name="setpersonality", description="Change the bot's AI personality and behavior.")
    @app_commands.describe(instruction="Describe exactly how the bot should act (e.g., 'Be a sassy cat').")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def set_personality(self, interaction: discord.Interaction, instruction: str):
        self.config["system_instruction"] = instruction
        self.save_config()
        # Clear history so the new personality takes over immediately
        self.chat_history = {}
        await interaction.response.send_message(f"🧠 **Personality Updated!**\nNew Instruction: *{instruction}*", ephemeral=True)

    @app_commands.command(name="resetchat", description="Clears the AI's memory of the current conversation.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def resetchat(self, interaction: discord.Interaction):
        channel_id = interaction.channel_id
        if channel_id in self.chat_history:
            del self.chat_history[channel_id]
        await interaction.response.send_message("🧹 **Memory wiped!** I've forgotten our previous chat context.", ephemeral=True)

    # =========================================================================
    # LISTENER: REPLIES TO MESSAGES (when the bot is mentioned or in a private chat)
    # =========================================================================

    @commands.Cog.listener()
    async def on_message(self, message):
        # Don't reply to itself or other bots
        if message.author.bot:
            return

        # Don't reply if the message is a command (starts with prefix)
        if message.content.startswith(self.bot.command_prefix):
            return

        # CONDITIONS TO REPLY (automatically):
        # 1. It's a Direct Message (DM) with the bot (1:1 chat)
        # 2. It's a Group DM
        # 3. The bot is explicitly mentioned (@Naekii) ANYWHERE (Server, Group DM, User DM)

        is_dm_channel = isinstance(message.channel, discord.DMChannel)
        is_group_channel = isinstance(message.channel, discord.GroupChannel)
        is_mentioned = self.bot.user in message.mentions

        # For User Apps, 'on_message' only fires in User-to-User DMs if the bot is mentioned.
        if is_dm_channel or is_group_channel or is_mentioned:
            # Show "Naekii is typing..." while generating response
            async with message.channel.typing():
                # Clean up the message content (remove the @mention if present)
                user_text = message.content.replace(f"<@{self.bot.user.id}>", "").strip()

                if not user_text and not message.attachments:
                    # User just pinged without text
                    user_text = "Hello!"

                response = await self.generate_response(message.channel.id, user_text, message.author.display_name)

                # Reply to the user
                await message.reply(response, mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))