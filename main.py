import sys
import asyncio
import logging
from typing import List

import discord
from discord.ext import commands
from discord import app_commands

from config import TOKEN, APPLICATION_ID, COMMAND_PREFIX
from cogs.music import Music
from cogs.interactions import InteractionHandler

sys.path.append(".")

intents = discord.Intents.default()
intents.message_content = True

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PlaygroundBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(COMMAND_PREFIX),
            description="Playground: Bot",
            intents=intents,
            application_id=APPLICATION_ID,
        )

    async def setup_hook(self):
        await self.load_extension("cogs.music")
        await self.load_extension("cogs.interactions")
        logger.info("Cogs loaded successfully")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")
        await self.sync_commands()

    async def sync_commands(self):
        try:
            logger.info("Attempting to sync commands...")
            synced: List[app_commands.Command] = await self.tree.sync()
            logger.info(f"Slash Commands synced: {len(synced)} commands")
            for command in synced:
                logger.info(f"Synced command: {command.name}")
            logger.info("Slash Commands synced successfully!")
        except Exception as e:
            logger.error(f"Unexpected error while syncing commands: {e}")


bot = PlaygroundBot()


@bot.tree.command(name="play", description="Play a song with given keyword!")
async def slash_play(interaction: discord.Interaction, keyword: str):
    music_cog: Music = bot.get_cog("Music")
    if music_cog:
        await music_cog.handle_play_command(interaction, keyword)
    else:
        await interaction.response.send_message("Music cog not found.", ephemeral=True)


@bot.tree.command(name="search", description="Search for songs and select one to play!")
async def slash_search(interaction: discord.Interaction, keyword: str):
    music_cog: Music = bot.get_cog("Music")
    if music_cog:
        await music_cog.handle_search_command(interaction, keyword)
    else:
        await interaction.response.send_message("Music cog not found.", ephemeral=True)

@bot.tree.command(name="now", description="Show the currently playing song!")
async def slash_now(interaction: discord.Interaction):
    music_cog: Music = bot.get_cog("Music")
    if music_cog:
        await music_cog.show_now_playing(interaction)
    else:
        await interaction.response.send_message("Music cog not found.", ephemeral=True)

@bot.tree.command(name="clear", description="Clear the current music queue")
async def slash_clear(interaction: discord.Interaction):
    music_cog: Music = bot.get_cog("Music")
    if music_cog:
        await music_cog.clear(interaction)
    else:
        await interaction.response.send_message("Music cog not found.", ephemeral=True)


async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
