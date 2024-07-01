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
        logger.info("--------------------------------")
        await self.tree.sync()
        logger.info("Commands synced successfully!")


bot = PlaygroundBot()


async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
