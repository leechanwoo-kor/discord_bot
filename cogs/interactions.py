import asyncio
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class InteractionHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            await self.handle_interaction(interaction)

    async def handle_interaction(self, interaction: discord.Interaction):
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

        handler = handlers.get(custom_id)
        if handler:
            try:
                await handler(interaction, music_cog, ctx)
            except Exception as e:
                logger.error(f"Error handling interaction {custom_id}: {e}")
                await interaction.response.send_message(
                    "An error occurred while processing your request.", ephemeral=True
                )
        else:
            logger.warning(f"No handler found for custom_id: {custom_id}")
            await interaction.response.send_message(
                "This interaction is not supported.", ephemeral=True
            )

    async def handle_pause_resume(self, interaction, music_cog, ctx):
        voice_client = interaction.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
            action = "paused"
        elif voice_client.is_paused():
            voice_client.resume()
            action = "resumed"
        else:
            await interaction.response.send_message(
                "No audio is currently playing.", ephemeral=True
            )
            return

        await music_cog.send_now_playing(ctx, music_cog.current)
        await interaction.response.send_message(f"Play {action}.", ephemeral=True)

    async def handle_skip(self, interaction, music_cog, ctx):
        try:
            if music_cog.now_playing_message:
                await music_cog.now_playing_message.delete()
            music_cog.now_playing_message = None
            if ctx.voice_client and ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await interaction.response.send_message(
                "Skipped the current song.", ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in handle_skip: {e}")
            await interaction.response.send_message(
                "An error occurred while trying to skip the song.", ephemeral=True
            )

    async def handle_stop(self, interaction, music_cog, ctx):
        if (
            interaction.guild.voice_client
            and interaction.guild.voice_client.is_connected()
        ):
            if music_cog.now_playing_message:
                await music_cog.now_playing_message.delete()
                music_cog.now_playing_message = None
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message(
                "Stopped play and disconnected from voice channel.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "I'm not currently in a voice channel.", ephemeral=True
            )

    async def handle_loop(self, interaction, music_cog, ctx):
        music_cog.loop = not music_cog.loop
        status = "enabled" if music_cog.loop else "disabled"
        await music_cog.send_now_playing(ctx, music_cog.current)
        await interaction.response.send_message(f"Loop mode {status}.", ephemeral=True)

    async def handle_show_queue(self, interaction, music_cog, ctx):
        await interaction.response.defer()
        await music_cog.send_queue(ctx)


async def setup(bot):
    await bot.add_cog(InteractionHandler(bot))
    logger.info("InteractionHandler cog loaded successfully")
