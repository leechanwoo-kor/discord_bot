import asyncio
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class InteractionHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def handle_interaction(self, interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id")
            if not custom_id:
                logger.error("Component interaction does not contain custom_id.")
                return

            music_cog = interaction.client.get_cog("Music")
            ctx = await interaction.client.get_context(interaction.message)

            handlers = {
                "pause_resume": self.handle_pause_resume,
                "skip": self.handle_skip,
                "stop": self.handle_stop,
                "loop": self.handle_loop,
                "show_queue": self.handle_show_queue,
            }

            if custom_id in handlers:
                await handlers[custom_id](interaction, music_cog, ctx)
        else:
            # Handle other types of interactions if needed
            pass

    async def handle_pause_resume(self, interaction, music_cog, ctx):
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
        elif interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
        await music_cog.send_now_playing(ctx, music_cog.current)

    async def handle_skip(self, interaction, music_cog, ctx):
        if music_cog.now_playing_message:
            await music_cog.now_playing_message.delete()
            music_cog.now_playing_message = None
        interaction.guild.voice_client.stop()
        await music_cog.send_now_playing(ctx, music_cog.current)

    async def handle_stop(self, interaction, music_cog, ctx):
        # if interaction.guild.voice_client.is_connected():
        if music_cog.now_playing_message:
            await music_cog.now_playing_message.delete()
            music_cog.now_playing_message = None
        await interaction.guild.voice_client.disconnect()

    async def handle_loop(self, interaction, music_cog, ctx):
        music_cog.loop = not music_cog.loop
        interaction.guild.voice_client.loop = music_cog.loop
        await music_cog.send_now_playing(ctx, music_cog.current)

    async def handle_show_queue(self, interaction, music_cog, ctx):
        await interaction.response.defer()
        await music_cog.send_queue(ctx)


async def setup(bot):
    cog = InteractionHandler(bot)
    await bot.add_cog(cog)
    bot.add_listener(cog.handle_interaction, "on_interaction")
