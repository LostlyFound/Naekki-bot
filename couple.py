import discord
from discord.ext import commands
from discord import app_commands, ui
import random
import json
import os
import string
import asyncio

LOVE_JAR_FILE = "love_jar.json"
SHARED_LISTS_FILE = "shared_lists.json"
HANGMAN_FILE = "hangman_games.json" # New file for Hangman state

# =========================================================================
# HANGMAN GAME VIEW (Buttons)
# This view manages the interactive letter buttons for guessing.
# =========================================================================

class HangmanGameView(ui.View):
    def __init__(self, cog, channel_id, game_data):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id
        self.game_data = game_data # Reference to the current game state

        # Create buttons for all letters A-Z
        for letter in string.ascii_uppercase:
            is_guessed = letter in self.game_data['guessed_letters']

            button = ui.Button(
                label=letter,
                style=discord.ButtonStyle.secondary if not is_guessed else discord.ButtonStyle.green if letter in self.game_data['word'] else discord.ButtonStyle.danger,
                custom_id=f"hangman_{letter}",
                disabled=is_guessed or self.game_data['status'] != 'active'
            )
            # Assign the callback function
            button.callback = self.button_callback
            self.add_item(button)

    # Overwrite the default add_item to control row layout
    def add_item(self, item: discord.ui.Item):
        # 26 letters in total, 7 per row (4 rows of 7, 1 row of 2)
        if len(self.children) < 7:
            item.row = 0
        elif len(self.children) < 14:
            item.row = 1
        elif len(self.children) < 21:
            item.row = 2
        else:
            item.row = 3
        super().add_item(item)

    async def button_callback(self, interaction: discord.Interaction):
        # Check if it's the right person guessing
        if interaction.user.id != self.game_data['guesser_id']:
            await interaction.response.send_message("❌ It's not your turn to guess, or you are not the designated guesser!", ephemeral=True)
            return

        # Get the letter from the custom_id (e.g., "hangman_A")
        letter = interaction.data['custom_id'].split('_')[1]

        # Process the guess and get the result message
        result_message = await self.cog.process_hangman_guess(self.channel_id, letter)

        # Update the message with the new view and content
        updated_embed = self.cog.create_hangman_embed(self.channel_id)

        # Recreate the view to update disabled state and color
        updated_view = HangmanGameView(self.cog, self.channel_id, self.game_data)

        await interaction.response.edit_message(embed=updated_embed, view=updated_view)

        # If the game is over, send a final celebratory/sad message
        if self.game_data['status'] != 'active':
            await interaction.followup.send(result_message)
            # Remove game state
            await self.cog.delete_hangman_game(self.channel_id)
            return

        # Send a follow-up message with the result (e.g., "Correct!" or "Wrong!")
        await interaction.followup.send(f"{interaction.user.mention}, {result_message}", ephemeral=False)


# =========================================================================
# COUPLES COG CLASS
# =========================================================================

class Couples(commands.Cog):
    """A Cog containing features specifically for couples."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.love_jar = self.load_json(LOVE_JAR_FILE, default_type=[])
        self.shared_lists = self.load_json(SHARED_LISTS_FILE, default_type={})
        self.hangman_games = self.load_json(HANGMAN_FILE, default_type={})

    # Utility method for loading/saving JSON data
    def load_json(self, filename, default_type):
        if not os.path.exists(filename):
            return default_type
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except:
            return default_type

    def save_json(self, filename, data):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    # --- HANGMAN GAME LOGIC HELPERS ---

    async def delete_hangman_game(self, channel_id):
        """Deletes the game state after a win, loss, or stop."""
        if channel_id in self.hangman_games:
            del self.hangman_games[channel_id]
            self.save_json(HANGMAN_FILE, self.hangman_games)

    def get_hangman_mask(self, word, guessed_letters):
        """Returns the masked word display (e.g., H E L L O -> H _ _ L O)"""
        masked = ""
        for char in word:
            if char.upper() in guessed_letters or char.upper() == ' ':
                masked += char.upper() + " "
            else:
                masked += "_ "
        return masked.strip()

    def check_hangman_win(self, word, guessed_letters):
        """Checks if all non-space letters have been guessed."""
        for char in word:
            if char.isalpha() and char.upper() not in guessed_letters:
                return False
        return True

    def get_hangman_art(self, mistakes):
        """Generates simple text-based hangman art."""
        stages = [
            # 0 Mistakes
            """
              ---
              |/
              | 
              |
              |
            __|__
            """,
            # 1 Mistake (Head)
            """
              ---
              |/  |
              |  ( )
              |
              |
            __|__
            """,
            # 2 Mistakes (Body)
            """
              ---
              |/  |
              |  ( )
              |   |
              |
            __|__
            """,
            # 3 Mistakes (Left Arm)
            """
              ---
              |/  |
              |  ( )
              |  /|
              |
            __|__
            """,
            # 4 Mistakes (Right Arm)
            """
              ---
              |/  |
              |  ( )
              |  /|\\
              |
            __|__
            """,
            # 5 Mistakes (Left Leg)
            """
              ---
              |/  |
              |  ( )
              |  /|\\
              |  /
            __|__
            """,
            # 6 Mistakes (Game Over - Right Leg)
            """
              ---
              |/  |
              |  (X)
              |  /|\\
              |  / \\
            __|__
            """
        ]
        return f"```\n{stages[mistakes]}\n```"

    def create_hangman_embed(self, channel_id):
        """Creates the main Discord Embed for the game state."""
        game = self.hangman_games[channel_id]

        setter_user = self.bot.get_user(game['setter_id'])
        guesser_user = self.bot.get_user(game['guesser_id'])

        title = f"❓ Hangman: Set by {setter_user.display_name}"
        color = discord.Color.blue()
        footer = f"Guessed Letters: {', '.join(sorted(game['guessed_letters']))}"

        if game['status'] == 'won':
            title = "🎉 Hangman Solved! 🎉"
            color = discord.Color.green()
        elif game['status'] == 'lost':
            title = "💀 Hangman Game Over 💀"
            color = discord.Color.red()
            footer += f" | Word was: {game['word']}"
        elif game['status'] == 'stopped':
             title = "🛑 Hangman Stopped 🛑"
             color = discord.Color.dark_grey()
             footer += f" | Word was: {game['word']}"

        embed = discord.Embed(title=title, color=color)

        # Display the ASCII art
        embed.add_field(
            name=f"Mistakes: {game['mistakes']}/{game['max_mistakes']}",
            value=self.get_hangman_art(game['mistakes']),
            inline=False
        )

        # Display the masked word
        masked_word = self.get_hangman_mask(game['word'], game['guessed_letters'])
        embed.add_field(
            name="Current Word/Phrase",
            value=f"## `{masked_word}`",
            inline=False
        )

        # Show current player
        if game['status'] == 'active' and guesser_user:
            embed.set_footer(text=f"Turn: {guesser_user.display_name} | {footer}")
        else:
            embed.set_footer(text=footer)

        return embed

    async def process_hangman_guess(self, channel_id, letter):
        """Processes a single letter guess, updates state, and checks for game end."""
        game = self.hangman_games[channel_id]
        letter = letter.upper()

        if game['status'] != 'active':
            return f"The game is already {game['status']}!"

        game['guessed_letters'].append(letter)

        word = game['word']

        if letter in word:
            # Correct guess
            if self.check_hangman_win(word, game['guessed_letters']):
                game['status'] = 'won'
                self.save_json(HANGMAN_FILE, self.hangman_games)
                return f"🎉 **SOLVED!** {self.bot.get_user(game['guesser_id']).display_name} nailed the phrase! It was **{word}**."
            else:
                self.save_json(HANGMAN_FILE, self.hangman_games)
                return f"✅ **Correct!** The letter **{letter}** is in the phrase."
        else:
            # Incorrect guess
            game['mistakes'] += 1

            if game['mistakes'] >= game['max_mistakes']:
                game['status'] = 'lost'
                self.save_json(HANGMAN_FILE, self.hangman_games)
                return f"💀 **GAME OVER!** Mistake {game['mistakes']}. You lost the round. The word was **{word}**."
            else:
                self.save_json(HANGMAN_FILE, self.hangman_games)
                return f"❌ **Wrong!** Mistake {game['mistakes']}/{game['max_mistakes']}."


    # =========================================================================
    # 🕹️ HANGMAN SLASH COMMANDS
    # =========================================================================

    @app_commands.command(name='hangman', description="Starts a game of Hangman (the inside-joke edition).")
    @app_commands.describe(action='What action to take?', target_user='The user who will guess the word (the setter is you).', phrase='The secret word/phrase (if starting the game).')
    @app_commands.choices(action=[
        app_commands.Choice(name="Start New Game", value="start"),
        app_commands.Choice(name="Stop Current Game", value="stop"),
    ])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def hangman_slash(self, interaction: discord.Interaction, action: app_commands.Choice[str], target_user: discord.User = None, phrase: str = None):
        channel_id = str(interaction.channel_id)

        if action.value == "start":
            if channel_id in self.hangman_games and self.hangman_games[channel_id]['status'] == 'active':
                await interaction.response.send_message("A Hangman game is already active in this channel! Use `/hangman stop` to end it.", ephemeral=True)
                return

            if not target_user or target_user.bot:
                await interaction.response.send_message("Please select a valid user (your partner!) to be the guesser using the `target_user` option.", ephemeral=True)
                return

            if target_user.id == interaction.user.id:
                 await interaction.response.send_message("You can't set a phrase and guess it yourself! Choose your partner.", ephemeral=True)
                 return

            if not phrase or len(phrase.strip()) < 3:
                await interaction.response.send_message("You must provide a secret `phrase` (min 3 characters). Make it an inside joke!", ephemeral=True)
                return

            # Sanitize phrase: keep only letters and spaces, convert to uppercase
            sanitized_phrase = "".join(c for c in phrase.upper() if c.isalpha() or c == ' ')

            # --- Initialize Game State ---
            self.hangman_games[channel_id] = {
                "word": sanitized_phrase.replace(" ", " "),
                "setter_id": interaction.user.id,
                "guesser_id": target_user.id,
                "guessed_letters": [],
                "mistakes": 0,
                "max_mistakes": 6,
                "status": "active"
            }
            self.save_json(HANGMAN_FILE, self.hangman_games)

            # Acknowledge the interaction and then edit the message to display the game
            await interaction.response.send_message(
                f"🎉 **Hangman Game Started!** 🎉\n"
                f"{interaction.user.mention} has set a secret phrase (an inside joke?) for {target_user.mention} to guess!\n"
                f"**Guesser:** {target_user.mention}. Guess a letter using the buttons below!",
                ephemeral=False
            )

            # Send the main interactive game message (Edit the response)
            game_embed = self.create_hangman_embed(channel_id)
            game_view = HangmanGameView(self, channel_id, self.hangman_games[channel_id])

            # Edit the original response to include the embed and buttons
            await interaction.edit_original_response(embed=game_embed, view=game_view, content="")

        elif action.value == "stop":
            if channel_id not in self.hangman_games or self.hangman_games[channel_id]['status'] != 'active':
                await interaction.response.send_message("There is no active Hangman game in this channel to stop.", ephemeral=True)
                return

            # Only the setter or an administrator can stop the game
            is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
            if interaction.user.id != self.hangman_games[channel_id]['setter_id'] and not is_admin:
                await interaction.response.send_message("Only the person who set the word can stop the game!", ephemeral=True)
                return

            # End the game and display the final word
            self.hangman_games[channel_id]['status'] = 'stopped'
            final_word = self.hangman_games[channel_id]['word']

            # Edit the message to show the final word and disable buttons
            game_embed = self.create_hangman_embed(channel_id)
            game_view = HangmanGameView(self, channel_id, self.hangman_games[channel_id])

            await interaction.response.send_message(f"🛑 **Game Stopped!** 🛑\n{interaction.user.mention} ended the game. The secret phrase was: **{final_word}**")

            # The original message needs to be edited to disable buttons, but since we sent a new response, 
            # we just delete the state now.
            await self.delete_hangman_game(channel_id)


    # =========================================================================
    # 💌 LOVE JAR COMMANDS
    # =========================================================================

    @app_commands.command(name="lovenote", description="Put a sweet note in the jar for your partner to find later.")
    @app_commands.describe(note="The sweet message you want to save.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def add_note(self, interaction: discord.Interaction, note: str):
        entry = {"user": interaction.user.display_name, "text": note}
        self.love_jar.append(entry)
        self.save_json(LOVE_JAR_FILE, self.love_jar)
        await interaction.response.send_message("💌 **Note added to the Love Jar!** Your partner can find it later.", ephemeral=True)

    @app_commands.command(name="openjar", description="Pull a random sweet note from the jar.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def open_jar(self, interaction: discord.Interaction):
        if not self.love_jar:
            await interaction.response.send_message("The jar is empty! Time to write some notes for each other. 📝", ephemeral=True)
            return

        note = random.choice(self.love_jar)
        embed = discord.Embed(
            title="💌 A Note from the Jar", 
            description=f"**\"{note['text']}\"**\n\n— *Left by {note['user']}*", 
            color=discord.Color.from_rgb(255, 182, 193) # Light pink
        )
        await interaction.response.send_message(embed=embed)

    # =========================================================================
    # 🤔 DECISION MAKER
    # =========================================================================

    @app_commands.command(name="decide", description="Can't agree? Let the bot decide! (Separate options with commas)")
    @app_commands.describe(options="List options separated by commas (e.g. Pizza, Sushi, Tacos)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def decide(self, interaction: discord.Interaction, options: str):
        # Split by comma and remove extra whitespace
        choices = [c.strip() for c in options.split(',') if c.strip()]

        if len(choices) < 2:
            await interaction.response.send_message("I need at least two options to decide! (e.g., `/decide options: Pizza, Sushi`)", ephemeral=True)
            return

        winner = random.choice(choices)

        embed = discord.Embed(title="🤔 The Decision Is...", color=discord.Color.gold())
        embed.add_field(name="Options", value=", ".join(choices), inline=False)
        embed.add_field(name="Winner", value=f"✨ **{winner}** ✨", inline=False)

        await interaction.response.send_message(embed=embed)

    # =========================================================================
    # 📝 SHARED LISTS
    # =========================================================================

    @app_commands.command(name="list", description="Manage shared lists (Movies, Groceries, Date Ideas).")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Item", value="add"),
        app_commands.Choice(name="View List", value="view"),
        app_commands.Choice(name="Remove Item", value="remove"),
        app_commands.Choice(name="Clear List", value="clear")
    ])
    @app_commands.describe(list_name="Name of the list (e.g. Movies)", item="Item to add/remove (only for add/remove actions)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def manage_list(self, interaction: discord.Interaction, action: app_commands.Choice[str], list_name: str, item: str = None):
        list_name = list_name.lower().strip()

        if action.value == "add":
            if not item:
                await interaction.response.send_message("You need to type the item you want to add!", ephemeral=True)
                return

            if list_name not in self.shared_lists:
                self.shared_lists[list_name] = []

            self.shared_lists[list_name].append(item)
            self.save_json(SHARED_LISTS_FILE, self.shared_lists)
            await interaction.response.send_message(f"✅ Added **{item}** to the **{list_name}** list!")

        elif action.value == "view":
            if list_name not in self.shared_lists or not self.shared_lists[list_name]:
                await interaction.response.send_message(f"The **{list_name}** list is currently empty.", ephemeral=True)
                return

            # Create a numbered list
            items_text = ""
            for i, val in enumerate(self.shared_lists[list_name], 1):
                items_text += f"**{i}.** {val}\n"

            embed = discord.Embed(title=f"📝 {list_name.capitalize()} List", description=items_text, color=discord.Color.teal())
            await interaction.response.send_message(embed=embed)

        elif action.value == "remove":
            if list_name not in self.shared_lists or not self.shared_lists[list_name]:
                await interaction.response.send_message(f"The **{list_name}** list is empty, nothing to remove.", ephemeral=True)
                return

            # Try to remove by exact match first
            if item in self.shared_lists[list_name]:
                self.shared_lists[list_name].remove(item)
                self.save_json(SHARED_LISTS_FILE, self.shared_lists)
                await interaction.response.send_message(f"🗑️ Removed **{item}** from **{list_name}**.")
                return

            # Try to remove by index number (e.g. user types "1")
            try:
                idx = int(item) - 1
                if 0 <= idx < len(self.shared_lists[list_name]):
                    removed = self.shared_lists[list_name].pop(idx)
                    self.save_json(SHARED_LISTS_FILE, self.shared_lists)
                    await interaction.response.send_message(f"🗑️ Removed **{removed}** from **{list_name}**.")
                else:
                    await interaction.response.send_message("Invalid number.", ephemeral=True)
            except ValueError:
                await interaction.response.send_message(f"Couldn't find **{item}** in the list.", ephemeral=True)

        elif action.value == "clear":
            if list_name in self.shared_lists:
                self.shared_lists[list_name] = []
                self.save_json(SHARED_LISTS_FILE, self.shared_lists)
                await interaction.response.send_message(f"💥 Cleared the entire **{list_name}** list.", ephemeral=True)
            else:
                await interaction.response.send_message("That list doesn't exist yet.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Couples(bot))