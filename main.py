import discord
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")


class MyClient(discord.Client):

    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        await self.tree.sync()
        print('Slash commands synced globally.')


@app_commands.command(name="hello")
@app_commands.describe(name="The name of the person to greet.")
async def hello_command(interaction: discord.Interaction, name: str):
    """Greets the user with a friendly message!"""
    await interaction.response.send_message(
        f'Hello, {name}! This bot is running Pycord v{discord.__version__}.')


@app_commands.command(name="ping")
async def ping_command(interaction: discord.Interaction):
    """Responds with Pong! and the bot's latency."""
    latency = round(client.latency * 1000)
    await interaction.response.send_message(f'Pong! 🚀 (Latency: {latency}ms)')


if __name__ == "__main__":
    intents = discord.Intents.default()

    client = MyClient(intents=intents)

    client.tree.add_command(hello_command)
    client.tree.add_command(ping_command)

    if DISCORD_TOKEN:
        try:
            client.run(DISCORD_TOKEN)
        except discord.errors.LoginFailure:
            print(
                "ERROR: Invalid Discord bot token provided. Check your DISCORD_TOKEN in the .env file."
            )
    else:
        print(
            "ERROR: DISCORD_TOKEN not found. Please create a .env file and add your bot token."
        )
