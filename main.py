import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands

from config import TOKEN, APPLICATION_ID, COMMAND_PREFIX

sys.path.append(".")

intents = discord.Intents.default()
intents.message_content = True

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlaygroundBot")
logger.setLevel(logging.DEBUG)


file_handler = RotatingFileHandler(
    "playground_bot.log", maxBytes=5 * 1024 * 1024, backupCount=5
)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


class PlaygroundBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(COMMAND_PREFIX),
            description="Playground: Bot",
            intents=intents,
            application_id=APPLICATION_ID,
        )

    async def setup_hook(self):
        try:
            await self.load_extension("cogs.music")
            await self.load_extension("cogs.interactions")
            logger.info("Cogs loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load cogs: {e}")
            raise

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("--------------------------------")
        try:
            await self.tree.sync()
            logger.info("Commands synced successfully!")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")


bot = PlaygroundBot()


async def main():
    try:
        async with bot:
            await bot.start(TOKEN)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unexpected error occurred: {e}")
