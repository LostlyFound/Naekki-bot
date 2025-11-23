import discord
from discord.ext import commands
from discord import app_commands
import requests
import random
import os
import asyncio
import datetime
import json

# =========================================================================
# 🎨 CUSTOMIZE YOUR CONTENT HERE
# =========================================================================

INSIDE_JOKES = [
    "Remember that time we got lost? 😂",
    "You're the 🧀 to my 🍷!",
    "Internal Error: Cuteness overload detected.",
    "That's what she said! (Or he said...)",
    "Don't make me use the 'look' 👀",
    "You owe me a soda! 🥤"
]

TRUTH_QUESTIONS = [
    "What is your biggest fear?",
    "What is the most embarrassing thing you've ever done?",
    "Have you ever lied to get out of trouble?",
    "Who is your secret crush? (Besides me 😉)",
    "What is your guilty pleasure movie?",
    "If you could change one thing about yourself, what would it be?"
]

DARE_TASKS = [
    "Send a selfie making a funny face right now!",
    "Do 10 jumping jacks and send a video (or voice note of you tired).",
    "Talk in a fake accent for the next 10 minutes.",
    "Send the 5th photo in your camera roll without explaining context.",
    "Text your parents/best friend and tell them you're becoming a mime.",
    "Draw a picture of me on paper and send it."
]

# =========================================================================

# --- Helper Data for Interaction Commands ---
INTERACTION_GIFS = {
    'hug': [
        "https://placehold.co/500x300/42a5f5/fff?text=A+BIG+HUG",
        "https://placehold.co/500x300/9ccc65/fff?text=CUDDLES",
        "https://placehold.co/500x300/ab47bc/fff?text=COMFY+HUG"
    ],
    'kiss': [
        "https://placehold.co/500x300/ef5350/fff?text=SWEET+KISS",
        "https://placehold.co/500x300/ffb300/fff?text=MUAH",
        "https://placehold.co/500x300/26a69a/fff?text=KISS"
    ]
}

COUNTDOWN_FILE = "countdowns.json"

class FunCommands(commands.Cog):
    """A Cog containing fun, relationship-focused slash and prefix commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.countdowns = self.load_countdowns()

    def load_countdowns(self):
        if not os.path.exists(COUNTDOWN_FILE):
            return {}
        try:
            with open(COUNTDOWN_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_countdowns(self):
        with open(COUNTDOWN_FILE, "w") as f:
            json.dump(self.countdowns, f, indent=4)

    # =========================================================================
    # SLASH COMMANDS (Invoked with /)
    # =========================================================================

    # --- NEW: INSIDE JOKES ---
    @app_commands.command(name='joke', description='Tells a random inside joke or quote.')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def joke_slash(self, interaction: discord.Interaction):
        joke = random.choice(INSIDE_JOKES)
        embed = discord.Embed(title="✨ Just Between Us...", description=joke, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    # --- NEW: TRUTH OR DARE ---
    @app_commands.command(name='truth', description='Asks a random Truth question.')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def truth_slash(self, interaction: discord.Interaction):
        question = random.choice(TRUTH_QUESTIONS)
        embed = discord.Embed(title="🔮 Truth", description=f"**{question}**", color=discord.Color.dark_blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='dare', description='Gives a random Dare task.')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def dare_slash(self, interaction: discord.Interaction):
        task = random.choice(DARE_TASKS)
        embed = discord.Embed(title="🔥 Dare", description=f"**{task}**", color=discord.Color.dark_orange())
        await interaction.response.send_message(embed=embed)

    # --- NEW: COUNTDOWN ---
    @app_commands.command(name='countdown', description='Manage countdowns. Format: YYYY-MM-DD')
    @app_commands.describe(action='Set a new date or check existing ones?', date='YYYY-MM-DD (Only needed for set)', title='Title of the event (Only needed for set)')
    @app_commands.choices(action=[
        app_commands.Choice(name="Set Date", value="set"),
        app_commands.Choice(name="Check Days", value="check"),
        app_commands.Choice(name="Delete All", value="delete")
    ])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def countdown_slash(self, interaction: discord.Interaction, action: app_commands.Choice[str], date: str = None, title: str = "Special Day"):
        user_id = str(interaction.user.id)

        if action.value == "set":
            if not date:
                await interaction.response.send_message("Please provide a date in YYYY-MM-DD format!", ephemeral=True)
                return

            try:
                # Validate date format
                target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                today = datetime.date.today()

                if target_date < today:
                     await interaction.response.send_message("That date is in the past! Unless you have a time machine? 🕰️", ephemeral=True)
                     return

                # Save to dictionary
                if user_id not in self.countdowns:
                    self.countdowns[user_id] = []

                self.countdowns[user_id].append({"title": title, "date": date})
                self.save_countdowns()

                await interaction.response.send_message(f"✅ Countdown set for **{title}** on **{date}**!")

            except ValueError:
                await interaction.response.send_message("Invalid date format! Please use **YYYY-MM-DD** (e.g., 2025-12-25).", ephemeral=True)

        elif action.value == "check":
            if user_id not in self.countdowns or not self.countdowns[user_id]:
                await interaction.response.send_message("You haven't set any countdowns yet! Use `/countdown action:Set Date`.", ephemeral=True)
                return

            embed = discord.Embed(title="📅 Your Countdowns", color=discord.Color.teal())
            today = datetime.date.today()

            # Calculate days remaining for each entry
            to_remove = []
            for index, entry in enumerate(self.countdowns[user_id]):
                try:
                    target_date = datetime.datetime.strptime(entry['date'], "%Y-%m-%d").date()
                    delta = (target_date - today).days

                    if delta < 0:
                        embed.add_field(name=f"~~{entry['title']}~~", value=f"Passed {abs(delta)} days ago", inline=False)
                        # Optional: Auto-delete passed events? For now, we keep them crossed out.
                    elif delta == 0:
                        embed.add_field(name=f"🎉 {entry['title']} 🎉", value="**IT IS TODAY!**", inline=False)
                    else:
                        embed.add_field(name=entry['title'], value=f"**{delta}** days remaining", inline=False)
                except ValueError:
                    to_remove.append(index)

            await interaction.response.send_message(embed=embed)

        elif action.value == "delete":
            if user_id in self.countdowns:
                del self.countdowns[user_id]
                self.save_countdowns()
                await interaction.response.send_message("🗑️ All your countdowns have been deleted.", ephemeral=True)
            else:
                 await interaction.response.send_message("You don't have any countdowns to delete.", ephemeral=True)

    # --- EXISTING COMMANDS (Updated contexts) ---

    @app_commands.command(name='meme', description='Fetches a random, meme from Reddit.')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def meme_slash(self, interaction: discord.Interaction):
        await interaction.response.defer() 
        MEME_API_URL = "https://meme-api.com/gimme/memes"
        try:
            response = await self.bot.loop.run_in_executor(None, lambda: requests.get(MEME_API_URL, timeout=10))
            response.raise_for_status() 
            data = response.json()
            embed = discord.Embed(title=data.get('title', 'A Random Meme'), url=data.get('postLink'), color=discord.Color.blue())
            embed.set_image(url=data.get('url'))
            embed.set_footer(text=f"From {data.get('subreddit')} | Requested by {interaction.user.name}")
            await interaction.followup.send(embed=embed)
        except requests.exceptions.RequestException:
            await interaction.followup.send("Oops! I couldn't fetch a meme right now.")

    @app_commands.command(name='hug', description='Sends a virtual hug to a user to show affection.')
    @app_commands.describe(user='The user you want to hug.')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def hug_slash(self, interaction: discord.Interaction, user: discord.User): 
        if user.id == interaction.user.id:
            await interaction.response.send_message("You can't hug yourself, silly! But I'll send one your way. 🤗", ephemeral=True)
            return
        gif_url = random.choice(INTERACTION_GIFS['hug'])
        embed = discord.Embed(title="🤗 Virtual Hug! 🤗", description=f"{interaction.user.mention} gives {user.mention} a big, loving hug! Aww...", color=discord.Color.purple())
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='kiss', description='Sends a virtual kiss to a user to show affection.')
    @app_commands.describe(user='The user you want to kiss.')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def kiss_slash(self, interaction: discord.Interaction, user: discord.User):
        if user.id == interaction.user.id:
            await interaction.response.send_message("Don't kiss and tell! I'll pretend I didn't see that. 😉", ephemeral=True)
            return
        gif_url = random.choice(INTERACTION_GIFS['kiss'])
        embed = discord.Embed(title="💋 Virtual Kiss! 💋", description=f"{interaction.user.mention} gives {user.mention} a sweet kiss! Hope you like it!", color=discord.Color.red())
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='coinflip', description='Flips a coin for a simple heads or tails game.')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def coinflip_slash(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        color = discord.Color.green() if result == "Heads" else discord.Color.dark_red()
        emoji = "👑" if result == "Heads" else "🐍"
        embed = discord.Embed(title=f"🪙 {interaction.user.name} flipped the coin! 🪙", description=f"The coin spins and lands on... **{result}**! {emoji}", color=color)
        await interaction.response.send_message(embed=embed)

    # =========================================================================
    # PREFIX COMMANDS (Invoked with e!)
    # =========================================================================
    # Note: Prefix commands do not need special decorators for DMs, they work if the bot can read the message.

    @commands.command(name='meme', help='Fetches a random, wholesome meme from Reddit.')
    async def meme_prefix(self, ctx: commands.Context):
        async with ctx.typing():
            MEME_API_URL = "https://meme-api.com/gimme/wholesomememes"
            try:
                response = await self.bot.loop.run_in_executor(None, lambda: requests.get(MEME_API_URL, timeout=10))
                response.raise_for_status()
                data = response.json()
                embed = discord.Embed(title=data.get('title', 'A Random Meme'), url=data.get('postLink'), color=discord.Color.blue())
                embed.set_image(url=data.get('url'))
                embed.set_footer(text=f"From {data.get('subreddit')} | Requested by {ctx.author.name}")
                await ctx.send(embed=embed)
            except requests.exceptions.RequestException:
                await ctx.send("Oops! I couldn't fetch a meme right now.")

    @commands.command(name='hug', help='Sends a virtual hug to a user to show affection.')
    async def hug_prefix(self, ctx: commands.Context, user: discord.User):
        if user.id == ctx.author.id:
            await ctx.send("You can't hug yourself, silly! But I'll send one your way. 🤗")
            return
        gif_url = random.choice(INTERACTION_GIFS['hug'])
        embed = discord.Embed(title="🤗 Virtual Hug! 🤗", description=f"{ctx.author.mention} gives {user.mention} a big, loving hug! Aww...", color=discord.Color.purple())
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name='kiss', help='Sends a virtual kiss to a user to show affection.')
    async def kiss_prefix(self, ctx: commands.Context, user: discord.User):
        if user.id == ctx.author.id:
            await ctx.send("Don't kiss and tell! I'll pretend I didn't see that. 😉")
            return
        gif_url = random.choice(INTERACTION_GIFS['kiss'])
        embed = discord.Embed(title="💋 Virtual Kiss! 💋", description=f"{ctx.author.mention} gives {user.mention} a sweet kiss! Hope you like it!", color=discord.Color.red())
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name='coinflip', help='Flips a coin for a simple heads or tails game.')
    async def coinflip_prefix(self, ctx: commands.Context):
        result = random.choice(["Heads", "Tails"])
        color = discord.Color.green() if result == "Heads" else discord.Color.dark_red()
        emoji = "👑" if result == "Heads" else "🐍"
        embed = discord.Embed(title=f"🪙 {ctx.author.name} flipped the coin! 🪙", description=f"The coin spins and lands on... **{result}**! {emoji}", color=color)
        await ctx.send(embed=embed)

    @commands.command(name='joke', help='Tells a random inside joke.')
    async def joke_prefix(self, ctx: commands.Context):
        joke = random.choice(INSIDE_JOKES)
        embed = discord.Embed(title="✨ Just Between Us...", description=joke, color=discord.Color.gold())
        await ctx.send(embed=embed)

    @commands.command(name='truth', help='Asks a random Truth question.')
    async def truth_prefix(self, ctx: commands.Context):
        question = random.choice(TRUTH_QUESTIONS)
        embed = discord.Embed(title="🔮 Truth", description=f"**{question}**", color=discord.Color.dark_blue())
        await ctx.send(embed=embed)

    @commands.command(name='dare', help='Gives a random Dare task.')
    async def dare_prefix(self, ctx: commands.Context):
        task = random.choice(DARE_TASKS)
        embed = discord.Embed(title="🔥 Dare", description=f"**{task}**", color=discord.Color.dark_orange())
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(FunCommands(bot))