from json import load
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import asyncio

from dotenv import load_dotenv


class Wakeup(commands.Cog):
    """A Cog for the custom Wakeup command integrated with a Webhook/IFTTT."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Load the secret Webhook URL from Replit Secrets
        self.webhook_url = os.getenv("ALEXA_WEBHOOK_URL")
        # Load authorized user IDs from environment variable
        self.allowed_users = self._load_allowed_users()

    def _load_allowed_users(self):
        """Loads and converts the comma-separated string of allowed user IDs."""
        user_ids_str = os.getenv("ALLOWED_USER_IDS")
        if not user_ids_str:
            print(
                "WARNING: ALLOWED_USER_IDS not set. Wakeup command will not work."
            )
            return []

        # Convert IDs to integers for comparison
        try:
            return [int(uid.strip()) for uid in user_ids_str.split(',')]
        except ValueError:
            print(
                "ERROR: ALLOWED_USER_IDS contains non-integer values. Please check the format."
            )
            return []

    async def _trigger_alexa_webhook(self, user_name):
        """Sends the HTTP request to the external service (e.g., IFTTT/Webhook)."""
        if not self.webhook_url:
            return "❌ **Configuration Error:** The `ALEXA_WEBHOOK_URL` secret is not set! I can't send the signal."

        if not self.allowed_users:
            return "❌ **Configuration Error:** The `ALLOWED_USER_IDS` secret is not set or formatted incorrectly! I don't know who is allowed."

        # Payload is sent to the webhook service. We use 'value1' to specify who triggered it.
        payload = {
            "value1": user_name,
            "value2": "Discord Wakeup Command",
            "value3": "Playing alarm/music now"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url,
                                        json=payload,
                                        timeout=5) as response:
                    if response.status == 200:
                        return f"🔔 **WAKEUP SIGNAL SENT!**\n> Alexa should be starting the alarm/music now. Get up, {user_name}!"
                    else:
                        error_text = await response.text()
                        print(
                            f"Webhook Failure: Status {response.status}, Response: {error_text}"
                        )
                        return f"⚠️ **Webhook Failed:** I sent the request, but the server responded with an error (Status: {response.status}). Check your `ALEXA_WEBHOOK_URL`."
        except asyncio.TimeoutError:
            return "⏱️ **Timeout Error:** The webhook server took too long to respond. The signal might still have been sent."
        except Exception as e:
            print(f"General Webhook Error: {e}")
            return "🚫 **Connection Error:** Something went wrong trying to contact the webhook service."

    # --- SLASH COMMAND (/wakeup) ---
    @app_commands.command(
        name='wakeup',
        description='Sends a signal to your linked Alexa device to wake you up.'
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True,
                                   dms=True,
                                   private_channels=True)
    async def wakeup_slash(self, interaction: discord.Interaction):
        # Authorization check
        if interaction.user.id not in self.allowed_users:
            await interaction.response.send_message(
                "❌ **Permission Denied:** You are not authorized to use this command.",
                ephemeral=True)
            return

        await interaction.response.defer(
        )  # Acknowledge interaction as the webhook may take a moment

        user_name = interaction.user.display_name
        response_text = await self._trigger_alexa_webhook(user_name)

        await interaction.followup.send(response_text)

    # --- PREFIX COMMAND (e!wakeup) ---
    @commands.command(
        name='wakeup',
        help='Sends a signal to your linked Alexa device to wake you up.')
    async def wakeup_prefix(self, ctx: commands.Context):
        # Authorization check
        if ctx.author.id not in self.allowed_users:
            await ctx.send(
                "❌ **Permission Denied:** You are not authorized to use this command."
            )
            return

        async with ctx.typing():
            user_name = ctx.author.display_name
            response_text = await self._trigger_alexa_webhook(user_name)
            await ctx.send(response_text)


async def setup(bot: commands.Bot):
    await bot.add_cog(Wakeup(bot))
