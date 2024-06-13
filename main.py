import sys
import asyncio
import discord
from discord.ext import commands
from config import TOKEN, APPLICATION_ID

sys.path.append(".")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="Relatively simple music bot example",
    intents=intents,
    application_id=APPLICATION_ID,
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("---------------------------------------------")
    asyncio.create_task(sync_commands())


async def sync_commands():
    try:
        print("Attempting to sync commands...")
        synced = await bot.tree.sync()
        print(f"Slash Command synced: {len(synced)} commands")
        for command in synced:
            print(f"Synced command: {command.name}")
        print("Slash Command sync complete.")
    except Exception as e:
        print(f"Unexpected error while syncing commands: {e}")


@bot.tree.command(name="play", description="play a song with given keyword!")
async def slash_play(interaction: discord.Interaction, keyword: str):
    music_cog = bot.get_cog("Music")
    if music_cog:
        await music_cog.handle_play_command(interaction, keyword)
    else:
        await interaction.response.send_message(
            "음악 cog를 찾을 수 없습니다.", ephemeral=True
        )


async def main():
    async with bot:
        try:
            await bot.load_extension("cogs.music")
            print("Loaded music cog")
        except Exception as e:
            print(f"Error loading music cog: {e}")

        try:
            await bot.load_extension("cogs.interactions")
            print("Loaded interactions cog")
        except Exception as e:
            print(f"Error loading interactions cog: {e}")

        await bot.start(TOKEN)


asyncio.run(main())
