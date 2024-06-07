import asyncio
import discord
from youtubesearchpython import VideosSearch
from discord.ext import commands
from utils.ytdl import YTDLSource
import discord.ui
from discord import InteractionType


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop = False
        self.current_url = None
        self.queue = []
        self.now_playing_message = None

    async def join_voice_channel(self, ctx):
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    async def create_player(self, url):
        return await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)

    async def play_next(self, ctx):
        if self.queue:
            next_url, next_title = self.queue.pop(0)
            await self.play_url(ctx, next_url, next_title)
        else:
            await ctx.send("Queue is empty.")

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            await self.join_voice_channel(ctx)
        else:
            await ctx.send("You are not connected to a voice channel.")
            raise commands.CommandError("Author not connected to a voice channel.")

    @commands.command(aliases=["p", "ㅔ"])
    async def play(self, ctx, *, keyword=None):
        if keyword:
            async with ctx.typing():
                videosSearch = VideosSearch(keyword, limit=1)
                result = videosSearch.result()["result"][0]
                url = result["link"]
                title = result["title"]

                self.queue.append((url, title))

                if (
                    not ctx.voice_client.is_playing()
                    and not ctx.voice_client.is_paused()
                ):
                    next_url, next_title = self.queue.pop(0)
                    await self.play_url(ctx, next_url, next_title)
                elif ctx.voice_client.is_playing():
                    # await ctx.send(f"added {title} to queue.")
                    await self.send_queue(ctx)
        else:
            if self.queue:
                next_url, next_title = self.queue.pop(0)
                await self.play_url(ctx, next_url, next_title)
            else:
                await ctx.send("Queue is empty.")
        await ctx.message.delete()

    def after_play(self, ctx, error):
        if error:
            print(f"Player error: {error}")
        coro = (
            self.play_next(ctx)
            if not self.loop
            else self.play_url(ctx, self.current_url, self.current_title)
        )
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Error resuming playback: {e}")

    async def play_url(self, ctx, url, title=""):
        try:
            if not isinstance(url, str) or not url:
                raise ValueError("The provided URL is not valid.")
            player = await self.create_player(url)
            ctx.voice_client.play(player, after=lambda e: self.after_play(ctx, e))
            self.current_url = url
            self.current_title = title
            await self.send_now_playing(ctx, url, title)
        except Exception as e:
            await ctx.send(f"Error playing URL: {e}")

    async def send_now_playing(self, ctx, url, title):
        max_title_length = 45
        if len(title) > max_title_length:
            title = title[: max_title_length - 3] + "..."

        videosSearch = VideosSearch(url, limit=1)
        result = videosSearch.result()["result"][0]
        thumbnail = result["thumbnails"][0]["url"]
        channel = result["channel"]["name"]
        views = result["viewCount"]["text"]
        duration = result["duration"]

        embed = discord.Embed(
            title=f"💿  Now Playing | {channel}",
            description=f"[{title}]({url})",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=thumbnail)
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="요청자", value=ctx.author.mention, inline=True)
        embed.add_field(name="음성채널", value=ctx.channel.name, inline=True)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="⏯️", style=discord.ButtonStyle.primary, custom_id="pause_resume"
            )
        )
        view.add_item(
            discord.ui.Button(
                label="⏭️", style=discord.ButtonStyle.secondary, custom_id="skip"
            )
        )
        view.add_item(
            discord.ui.Button(
                label="⏹️", style=discord.ButtonStyle.danger, custom_id="stop"
            )
        )
        view.add_item(
            discord.ui.Button(
                label="🔁", style=discord.ButtonStyle.secondary, custom_id="toggle_loop"
            )
        )
        view.add_item(
            discord.ui.Button(
                label="⏏️",
                style=discord.ButtonStyle.secondary,
                custom_id="show_queue",
            )
        )

        if self.now_playing_message:
            await self.now_playing_message.delete()

        self.now_playing_message = await ctx.send(embed=embed, view=view)

    async def send_queue(self, ctx):
        if not self.queue:
            await ctx.send("Queue is empty.")
        else:
            max_title_length = 45
            queue_list = "\n".join(
                [
                    f"{idx + 1}. {title[: max_title_length - 3] + '...' if len(title) > max_title_length else title}"
                    for idx, (url, title) in enumerate(self.queue)
                ]
            )
            current = (
                self.current_title[: max_title_length - 3] + '...' if len(self.current_title) > max_title_length else self.current_title
                if self.current_title
                else "No song is currently playing."
            )
            embed = discord.Embed(
                title="🎶 Current Queue",
                description=f"**Now Playing:** {current}\n\n**Up Next:**\n{queue_list}",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed, delete_after=5)

    @commands.command()
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):
        if self.now_playing_message:
            await self.now_playing_message.delete()
            self.now_playing_message = None
        await ctx.voice_client.disconnect()

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client.is_paused() or not ctx.voice_client.is_playing():
            return await ctx.send(
                "음악이 이미 일시 정지 중이거나 재생 중이지 않습니다."
            )
        ctx.voice_client.pause()

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client.is_playing() or not ctx.voice_client.is_paused():
            return await ctx.send(
                "음악이 이미 재생 중이거나 재생할 음악이 존재하지 않습니다."
            )
        ctx.voice_client.resume()

    @commands.command()
    async def loop(self, ctx):
        self.loop = not self.loop
        await ctx.send(f"Loop is now {'enabled' if self.loop else 'disabled'}.")

    @commands.command()
    async def show_queue(self, ctx):
        await self.send_queue(ctx)

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client.is_playing():
            if self.now_playing_message:
                await self.now_playing_message.delete()
                self.now_playing_message = None
            ctx.voice_client.stop()
        else:
            await ctx.send("No song is currently playing.")

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await self.join_voice_channel(ctx)
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")


async def handle_interaction(interaction):
    custom_id = interaction.data["custom_id"]
    music_cog = interaction.client.get_cog("Music")

    if custom_id == "pause_resume":
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message(
                "음악을 일시정지 했습니다.", ephemeral=True, delete_after=5
            )
        elif interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message(
                "음악을 다시 재생합니다.", ephemeral=True, delete_after=5
            )
        else:
            await interaction.response.send_message(
                "재생 중인 음악이 없습니다.", ephemeral=True, delete_after=5
            )

    elif custom_id == "skip":
        if interaction.guild.voice_client.is_playing():
            if music_cog.now_playing_message:
                await music_cog.now_playing_message.delete()
                music_cog.now_playing_message = None
            interaction.guild.voice_client.stop()
        else:
            await interaction.response.send_message(
                "No song is currently playing.", ephemeral=True
            )

    elif custom_id == "stop":
        if interaction.guild.voice_client.is_connected():
            if music_cog.now_playing_message:
                await music_cog.now_playing_message.delete()
                music_cog.now_playing_message = None
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message(
                "음악을 중지했습니다.", ephemeral=True, delete_after=5
            )
        else:
            await interaction.response.send_message(
                "봇이 음성 채널에 연결되어 있지 않습니다.",
                ephemeral=True,
                delete_after=5,
            )

    elif custom_id == "toggle_loop":
        music_cog.loop = not music_cog.loop
        await interaction.response.send_message(
            f"Loop is now {'enabled' if music_cog.loop else 'disabled'}.",
            ephemeral=True,
            delete_after=5,
        )

    elif custom_id == "show_queue":
        await interaction.response.defer()
        if not music_cog.queue:
            await interaction.followup.send("Queue is empty.", ephemeral=True)
        else:
            queue_list = "\n".join(
                [
                    f"{idx + 1}. {title}"
                    for idx, (url, title) in enumerate(music_cog.queue)
                ]
            )
            current = interaction.guild.voice_client.source.title if interaction.guild.voice_client and interaction.guild.voice_client.is_playing() else "No song is currently playing."
            embed = discord.Embed(
                title="🎶 Current Queue",
                description=f"**Now Playing:** {current}\n\n**Up Next:**\n{queue_list}",
                color=discord.Color.green(),
            )
            await interaction.followup.send(
                embed=embed, ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Music(bot))
    bot.add_listener(handle_interaction, "on_interaction")
