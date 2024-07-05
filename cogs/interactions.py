import asyncio
import logging

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class InteractionHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.interaction_handlers = {
            "pause_resume": self.handle_pause_resume,
            "skip": self.handle_skip,
            "stop": self.handle_stop,
            "loop": self.handle_loop,
            "show_queue": self.handle_show_queue,
        }

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            await self.handle_interaction(interaction)

    async def handle_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id")
        if not custom_id:
            logger.error("Component interaction does not contain custom_id.")
            return

        handler = self.interaction_handlers.get(custom_id)
        if handler:
            await self._execute_handler(handler, interaction)
        else:
            logger.error(f"No handler found for custom_id: {custom_id}")

    async def _execute_handler(self, handler, interaction):
        try:
            music_cog = interaction.client.get_cog("Music")
            ctx = await interaction.client.get_context(interaction.message)
            await handler(interaction, music_cog, ctx)
        except discord.errors.InteractionResponded:
            logger.warning(
                f"Interaction {interaction.id} has already been responded to."
            )
        except Exception as e:
            logger.error(f"Error handling interaction {interaction.id}: {e}")

    async def handle_pause_resume(self, interaction, music_cog, ctx):
        voice_client = interaction.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
            action = "paused"
        elif voice_client.is_paused():
            voice_client.resume()
            action = "resumed"

        await music_cog.send_now_playing(ctx, music_cog.current)

    async def handle_skip(self, interaction, music_cog, ctx):
        if music_cog.now_playing_message:
            await music_cog.now_playing_message.delete()
        music_cog.now_playing_message = None
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    async def handle_stop(self, interaction, music_cog, ctx):
        if (
            interaction.guild.voice_client
            and interaction.guild.voice_client.is_connected()
        ):
            if music_cog.now_playing_message:
                await music_cog.now_playing_message.delete()
                music_cog.now_playing_message = None
            await interaction.guild.voice_client.disconnect()

    async def handle_loop(self, interaction, music_cog, ctx):
        music_cog.loop = not music_cog.loop
        await music_cog.send_now_playing(ctx, music_cog.current)

    async def handle_show_queue(self, interaction, music_cog, ctx):
        await interaction.response.defer()
        await music_cog.send_queue(ctx)


async def setup(bot):
    await bot.add_cog(InteractionHandler(bot))
    logger.info("InteractionHandler cog loaded successfully")
