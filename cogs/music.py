import asyncio
import logging
from youtubesearchpython import VideosSearch

from typing import List, Optional

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

from utils.utils import ellipsis, get_translation
from utils.ytdl import YTDLSource

logger = logging.getLogger(__name__)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop = False
        self.current = None
        self.queue = []
        self.now_playing_message = None

    async def create_player(self, url):
        return await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)

    def get_user_locale(self, ctx):
        # TODO: Implement user locale detection
        return "ko"

    # Command handlers
    @app_commands.command(name="play", description="Play a song with given keyword")
    async def slash_play(self, interaction: discord.Interaction, keyword: str):
        await self.handle_play_command(interaction, keyword)

    @app_commands.command(name="search", description="Search songs with given keyword")
    async def slash_search(self, interaction: discord.Interaction, keyword: str):
        await self.handle_search_command(interaction, keyword)

    @app_commands.command(name="now", description="Show the currently playing song")
    async def slash_now(self, interaction: discord.Interaction):
        await self.show_now_playing(interaction)

    @app_commands.command(name="clear", description="Clear the current music queue")
    async def slash_clear(self, interaction: discord.Interaction):
        await self.clear(interaction)

    async def play_url(self, ctx, current):
        try:
            self.current = current
            url = current["link"]
            player = await self.create_player(url)
            ctx.voice_client.play(player, after=lambda e: self.after_play(ctx, e))
            await self.send_now_playing(ctx, current)
        except Exception as e:
            logger.error(f"Error playing URL: {e}")
            await ctx.send(f"Error playing URL: {e}")

    async def send_now_playing(self, ctx, current):
        try:
            locale = self.get_user_locale(ctx)
            embed = self.create_now_playing_embed(ctx, current, locale)
            view = self.create_view()

            now = await ctx.send(embed=embed, view=view)

            if self.now_playing_message:
                await self.delete_previous_now_playing_message()

            self.now_playing_message = now
        except Exception as e:
            logger.error(f"Error sending now playing message: {e}")
            await ctx.send(
                "An error occurred while trying to display the now playing message."
            )

    async def delete_previous_now_playing_message(self):
        try:
            await self.now_playing_message.delete()
        except discord.errors.NotFound:
            logger.warning(
                "Could not delete previous now playing message. It may have been already deleted."
            )
        except discord.errors.HTTPException as e:
            logger.error(f"Failed to delete previous message: {e}")

    @commands.command(aliases=["p", "P", "ㅔ"])
    async def play(self, ctx, *, keyword=None):
        await self.play_command(ctx, keyword)

    async def play_command(self, ctx, keyword=None):
        locale = self.get_user_locale(ctx)
        if not keyword:
            await ctx.send(get_translation("enter_keyword", locale))
            return

        async with ctx.typing():
            video_search = VideosSearch(keyword, limit=1)
            result = video_search.result()["result"][0]
            self.queue.append(result)

            if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                await self.play_url(ctx, self.queue.pop(0))
            else:
                await self.send_queue(ctx)

    def after_play(self, ctx, error):
        if error:
            logger.error(f"Player error: {error}")
        coro = self.play_next(ctx)
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result()
        except Exception as e:
            logger.error(f"Error resuming playback: {e}")

    async def play_next(self, ctx):
        if self.queue:
            next_item = self.queue.pop(0)
            await self.play_url(ctx, next_item)
        elif self.loop and self.current:
            await self.play_url(ctx, self.current)
        else:
            self.current = None
            locale = self.get_user_locale(ctx)
            await ctx.send(get_translation("queue_empty", locale))

    def create_now_playing_embed(self, ctx, current, locale):
        url = current["link"]
        title = ellipsis(current["title"])
        thumbnail = current["thumbnails"][0]["url"]
        channel = current["channel"]["name"]
        duration = current["duration"]

        play_status = "⏸️" if ctx.voice_client.is_paused() else "▶️"
        loop_status = "Y" if self.loop else "N"

        embed = discord.Embed(
            title=f"{play_status}  {get_translation('playing_now', locale)}  💿  | {channel}",
            description=f"[{title}]({url})",
            color=discord.Color.lighter_grey(),
        )
        embed.set_thumbnail(url=thumbnail)
        embed.add_field(
            name=get_translation("length", locale), value=duration, inline=True
        )
        embed.add_field(
            name=get_translation("requester", locale),
            value=ctx.author.mention,
            inline=True,
        )
        embed.add_field(
            name=get_translation("loop", locale), value=loop_status, inline=True
        )
        return embed

    def create_view(self):
        view = discord.ui.View()
        buttons = [
            ("⏯️", discord.ButtonStyle.primary, "pause_resume"),
            ("⏭️", discord.ButtonStyle.secondary, "skip"),
            ("⏹️", discord.ButtonStyle.danger, "stop"),
            ("🔁", discord.ButtonStyle.secondary, "loop"),
            ("⏏️", discord.ButtonStyle.secondary, "show_queue"),
        ]
        for label, style, custom_id in buttons:
            view.add_item(
                discord.ui.Button(label=label, style=style, custom_id=custom_id)
            )
        return view

    async def send_queue(self, ctx):
        locale = self.get_user_locale(ctx)
        if not self.queue:
            embed = discord.Embed(
                description=get_translation("queue_empty", locale),
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)
        else:
            now = ellipsis(self.current["title"])
            queue_list = ""
            view = View()

            for idx, video in enumerate(self.queue):
                title = ellipsis(video["title"], 45)
                queue_list += f"{idx + 1}. {title}\n"

                button = Button(
                    label=f"{idx + 1}",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"play_{idx}",
                )
                button.callback = self.queue_button_callback
                view.add_item(button)

            embed = discord.Embed(
                title=get_translation("current_queue", locale),
                description=f"**{get_translation('playing_now', locale)}:** {now}\n\n**{get_translation('up_next', locale)}:**\n{queue_list}",
                color=discord.Color.green(),
            )

            self.now_playing_message = await ctx.send(embed=embed, view=view)

    async def queue_button_callback(self, interaction):
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("play_"):
            index = int(custom_id.split("_")[1])
            if index < len(self.queue):
                selected_song = self.queue.pop(index)

                if interaction.guild.voice_client.is_playing():
                    interaction.guild.voice_client.stop()

                self.queue.insert(0, selected_song)

                await self.play_next(await self.bot.get_context(interaction))
            else:
                await interaction.response.send_message(
                    "Invalid song selection.", ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "Error processing button click.", ephemeral=True
            )

    @commands.command()
    async def volume(self, ctx, volume: int):
        locale = self.get_user_locale(ctx)
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(get_translation("volume_changed", locale, volume=volume))

    @play.before_invoke
    async def ensure_voice(self, ctx):
        locale = self.get_user_locale(ctx)
        if ctx.voice_client is None:
            if ctx.author.voice:
                await self.join_voice_channel(ctx)
            else:
                message = get_translation("join_voice_channel", locale)
                await ctx.send(message, ephemeral=True)
                raise commands.CommandError(message)

    async def join_voice_channel(self, ctx):
        if not ctx.author.voice:
            raise commands.CommandError(
                get_translation("join_voice_channel", self.get_user_locale(ctx))
            )

        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()

    @commands.command()
    async def reset(self, ctx):
        self.__init__(self.bot)
        await ctx.send("Reset complete.")
        await ctx.voice_client.disconnect()

    async def handle_play_command(self, interaction, keyword):
        class Context:
            def __init__(self, interaction, keyword):
                self.interaction = interaction
                self.author = interaction.user
                self.voice_client = interaction.guild.voice_client
                self.send = interaction.followup.send
                self.typing = interaction.channel.typing
                self.message = interaction.message
                self.guild = interaction.guild

        ctx = Context(interaction, keyword)
        locale = self.get_user_locale(ctx)

        if ctx.voice_client is None:
            if ctx.author.voice:
                await self.join_voice_channel(ctx)
            else:
                message = get_translation("join_voice_channel", locale)
                await interaction.response.send_message(message, ephemeral=True)
                return

        ctx.voice_client = ctx.guild.voice_client
        await interaction.response.defer()
        await self.play_command(ctx, keyword)

    async def handle_search_command(self, interaction, keyword):
        locale = self.get_user_locale(interaction)
        if not keyword:
            await interaction.response.send_message(
                get_translation("enter_keyword", locale)
            )
            return

        async with interaction.channel.typing():
            videosSearch = VideosSearch(keyword, limit=5)
            results = videosSearch.result()["result"]

            if not results:
                await interaction.response.send_message(
                    get_translation("no_results", locale)
                )
                return

            await interaction.response.send_message(
                get_translation("search_list", locale),
                view=SearchView(results, self, interaction),
            )

    async def play_selected(self, interaction, selected_result):
        class Context:
            def __init__(self, interaction, selected_result):
                self.interaction = interaction
                self.author = interaction.user
                self.voice_client = interaction.guild.voice_client
                self.send = interaction.followup.send
                self.typing = interaction.channel.typing
                self.message = interaction.message
                self.guild = interaction.guild

        ctx = Context(interaction, selected_result)
        locale = self.get_user_locale(ctx)

        if ctx.voice_client is None:
            if ctx.author.voice:
                await self.join_voice_channel(ctx)
            else:
                message = get_translation("join_voice_channel", locale)
                await interaction.response.send_message(message, ephemeral=True)
                return

        ctx.voice_client = ctx.guild.voice_client
        self.queue.append(selected_result)
        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            await self.play_url(ctx, self.queue.pop(0))
        else:
            await self.send_queue(ctx)

    async def show_now_playing(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        locale = self.get_user_locale(ctx)
        if self.current:
            embed = self.create_now_playing_embed(ctx, self.current, locale)
            view = self.create_view()
            await interaction.response.send_message(embed=embed, view=view)
        else:
            if self.queue:
                next_song = self.queue[0]["title"]
                message = f"No song is currently playing. Next up: {next_song}"
            else:
                message = "No song is currently playing and the queue is empty."
            await interaction.response.send_message(message, ephemeral=True)

    async def clear(self, interaction: discord.Interaction):
        locale = self.get_user_locale(interaction)
        if not self.queue:
            await interaction.response.send_message(
                "대기열이 이미 비어있습니다.", ephemeral=True
            )
        else:
            self.queue.clear()
            await interaction.response.send_message("대기열이 초기화되었습니다.")

    # Error handling
    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, discord.errors.Forbidden):
            await ctx.send("I don't have the required permissions to do that.")
        elif isinstance(error, commands.CommandError):
            await ctx.send(str(error))
        else:
            logger.error(f"An error occurred: {error}")
            await ctx.send("An unexpected error occurred. Please try again later.")


async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(Music(bot))
        logger.info("Music cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Music cog: {e}")
        raise


class SearchSelect(discord.ui.Select):
    def __init__(self, results, cog, interaction):
        self.results = results
        self.cog = cog
        self.interaction = interaction
        options = [
            discord.SelectOption(
                label=result["title"],
                description=result["channel"]["name"],
                value=str(index),
            )
            for index, result in enumerate(results)
        ]
        super().__init__(
            placeholder="Choose a song...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_index = int(self.values[0])
        selected_result = self.results[selected_index]
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except discord.errors.InteractionResponded:
            pass
        await self.cog.play_selected(interaction, selected_result)


class SearchView(discord.ui.View):
    def __init__(self, results, cog, interaction):
        super().__init__()
        self.add_item(SearchSelect(results, cog, interaction))
