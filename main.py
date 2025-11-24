import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from discord import app_commands
from webserver import keep_alive

COMMAND_PREFIX = 'e!'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)
tree = bot.tree

# Define the channel types considered "private" for prefix command responses
PRIVATE_CHANNELS = (discord.ChannelType.private, discord.ChannelType.group)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

    # --- Load Cogs ---
    # The bot loads the extension 'fun'. This finds the 'fun.py' file
    # and executes its setup function, registering all commands.
    try:
        await bot.load_extension('fun')
        print("Successfully loaded FunCommands cog.")
    except Exception as e:
        print(f"Failed to load FunCommands cog: {e}")

    try:
        await bot.load_extension('music_cog')
        print("Successfully loaded Music cog.")
    except Exception as e:
        print(f"Failed to load Music cog: {e}")

    try:
        await bot.load_extension('ai_chat')
        print("Successfully loaded AI chat cog.")
    except Exception as e:
        print(f"Failed to load AI chat cog: {e}")

    try:
        await bot.load_extension('wakeup')
        print("Successfully loaded Wakeup cog.")
    except Exception as e:
        print(f"Failed to load wakeup cog: {e}")

    try:
        await bot.load_extension('webhook_server')
        print("Successfully loaded Webhook server cog.")
    except Exception as e:
        print(f"Failed to load webhook server cog: {e}")

    try:
        await bot.load_extension('couple')
        print("Successfully loaded Couple cog.")
    except Exception as e:
        print(f"Failed to load Couple cog: {e}")

    # --- Sync Application Commands ---
    # This syncs both the commands defined in main.py AND the commands
    # loaded from the 'fun' cog.
    try:
        synced = await tree.sync()
        print(f'Synced {len(synced)} application commands globally.')
    except Exception as e:
        print(f"Error syncing application commands: {e}")

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name=f'{COMMAND_PREFIX}help or /help | Cogs loaded!'))


# --- CORE SLASH COMMANDS (Kept in main file) ---


@tree.command(
    name='greet',
    description='Greets you and tells you where the command was used.')
async def greet_slash(interaction: discord.Interaction):
    channel_type = interaction.channel.type

    if channel_type == discord.ChannelType.private:
        response_text = "I received your global slash command! It works perfectly in DMs/GMs."
        ephemeral_status = True
    elif channel_type == discord.ChannelType.group:
        response_text = "Hello from the group chat! Your global slash command works here."
        ephemeral_status = False
    else:
        response_text = f"Hello {interaction.user.mention}! This command was used globally in a server channel."
        ephemeral_status = False

    await interaction.response.send_message(response_text,
                                            ephemeral=ephemeral_status)


# --- LEGACY PREFIX COMMANDS (Kept in main file) ---


@bot.command(
    name='hello',
    help='Responds with a friendly greeting in DMs, GMs, and servers.')
async def hello_command(ctx: commands.Context):
    if ctx.channel.type in PRIVATE_CHANNELS:
        await ctx.send(
            f"Hello, {ctx.author.name}! We're chatting in private or a group. What's up?"
        )
    else:
        await ctx.send(f'Hi there, {ctx.author.mention}!')


@bot.command(name='dmtest',
             help='A command to confirm the bot works in DMs and Group DMs.')
async def dm_test_command(ctx: commands.Context):
    if ctx.channel.type in PRIVATE_CHANNELS:
        await ctx.send(
            f"Success! I can read your private messages/groups, {ctx.author.name}. I'm ready to chat!"
        )
    else:
        await ctx.send(
            f"This command is best used in a private chat or group message with me. Try sending me a DM, {ctx.author.mention}!"
        )


keep_alive()

# Load token from environment variable
load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if BOT_TOKEN is None:
    print(
        "\n\n!! CRITICAL: BOT_TOKEN is missing. Please set the 'DISCORD_BOT_TOKEN' environment variable. !!\n\n"
    )
else:
    try:
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        print(
            "Error: Invalid token was provided. Please check the 'DISCORD_BOT_TOKEN' environment variable."
        )
