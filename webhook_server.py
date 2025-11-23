import discord
from discord.ext import commands
import aiohttp
from aiohttp import web
import asyncio
import os

class WebhookServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        # Route for Alexa/IFTTT Triggers (POST)
        self.app.router.add_post('/alexa-trigger', self.handle_trigger)
        # Route for Uptime/Keep-Alive (GET) - This is the new part!
        self.app.router.add_get('/', self.handle_keep_alive)

        self.runner = None
        self.site = None
        self.server_task = self.bot.loop.create_task(self.start_server())

    def cog_unload(self):
        """Cleanup when the bot shuts down or reloads."""
        if self.server_task:
            self.server_task.cancel()
        self.bot.loop.create_task(self.close_server())

    async def handle_keep_alive(self, request):
        """A simple endpoint for UptimeRobot to ping."""
        return web.Response(text="I am alive! 🤖", status=200)

    async def handle_trigger(self, request):
        """Handle incoming requests from Alexa/IFTTT."""
        auth_header = request.headers.get('Authorization')
        expected_token = os.getenv("WEBHOOK_AUTH_TOKEN")

        if not expected_token or auth_header != expected_token:
            return web.Response(text="Unauthorized", status=401)

        try:
            data = await request.json()
            action = data.get('action', 'default')

            channel_id_str = os.getenv("DEFAULT_CHANNEL_ID")
            if not channel_id_str:
                return web.Response(text="Missing Channel Config", status=500)

            channel = self.bot.get_channel(int(channel_id_str))
            if not channel:
                return web.Response(text="Channel Not Found", status=404)

            if action == "hello":
                await channel.send("👋 **Alexa just said hello!** Hi everyone!")
            elif action == "joke":
                await channel.send("Alexa requested a joke... why did the chicken cross the road? To get to the other side!")
            elif action == "alert":
                await channel.send("🚨 **ALERT:** Alexa initiated a priority notification!")
            else:
                await channel.send(f"🤖 Alexa sent a signal: `{action}`")

            return web.Response(text="Success", status=200)

        except Exception as e:
            print(f"Webhook Error: {e}")
            return web.Response(text=str(e), status=500)

    async def start_server(self):
        """Starts the aiohttp web server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        # Replit listens on port 8080
        self.site = web.TCPSite(self.runner, '0.0.0.0', 8080)
        await self.site.start()
        print("🌐 Webhook Server listening on port 8080")

    async def close_server(self):
        """Stops the web server."""
        if self.runner:
            await self.runner.cleanup()

async def setup(bot: commands.Bot):
    await bot.add_cog(WebhookServer(bot))