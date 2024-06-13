import sys
import asyncio
import logging
import discord
from discord.ext import commands
from config import TOKEN, APPLICATION_ID

sys.path.append(".")

intents = discord.Intents.default()
intents.message_content = True

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="Relatively simple music bot example",
    intents=intents,
    application_id=APPLICATION_ID,
)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("---------------------------------------------")
    asyncio.create_task(sync_commands())


async def sync_commands():
    try:
        logger.info("Attempting to sync commands...")
        synced = await bot.tree.sync()
        logger.info(f"Slash Command synced: {len(synced)} commands")
        for command in synced:
            logger.info(f"Synced command: {command.name}")
        logger.info("Slash Command sync complete.")
    except Exception as e:
        logger.error(f"Unexpected error while syncing commands: {e}")


@bot.tree.command(name="play", description="play a song with given keyword!")
async def slash_play(interaction: discord.Interaction, keyword: str):
    music_cog = bot.get_cog("Music")
    if music_cog:
        await music_cog.handle_play_command(interaction, keyword)
    else:
        await interaction.response.send_message(
            "음악 cog를 찾을 수 없습니다.", ephemeral=True
        )


@bot.tree.command(name="search", description="Search for songs and select one to play!")
async def slash_search(interaction: discord.Interaction, keyword: str):
    music_cog = bot.get_cog("Music")
    if music_cog:
        await music_cog.handle_search_command(interaction, keyword)
    else:
        await interaction.response.send_message(
            "음악 cog를 찾을 수 없습니다.", ephemeral=True
        )


async def main():
    async with bot:
        try:
            await bot.load_extension("cogs.music")
            logger.info("Loaded music cog")
        except Exception as e:
            logger.error(f"Error loading music cog: {e}")

        try:
            await bot.load_extension("cogs.interactions")
            logger.info("Loaded interactions cog")
        except Exception as e:
            logger.error(f"Error loading interactions cog: {e}")

        await bot.start(TOKEN)


asyncio.run(main())
