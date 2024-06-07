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
        self.current_index = -1

    async def join_voice_channel(self, ctx):
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    async def create_player(self, url):
        return await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)

    async def play_next(self, ctx):
        self.current_index += 1
        if self.current_index < len(self.queue):
            next_url, next_title = self.queue[self.current_index]
            await self.play_url(ctx, next_url, next_title)
        else:
            self.current_index = -1
            await ctx.send("Queue is empty.")

    async def send_help_message(self, ctx):
        help_text = (
            "**Music Bot Commands:**\n"
            "`!join` - 음성 채널에 봇을 연결합니다.\n"
            "`!play [검색어]` - 검색어로 유튜브 영상을 찾아 재생합니다.\n"
            "`!volume [1-100]` - 볼륨을 조절합니다.\n"
            "`!stop` - 음악 재생을 멈추고 음성 채널에서 봇을 분리합니다.\n"
            "`!pause` - 음악을 일시 정지합니다.\n"
            "`!resume` - 일시 정지된 음악을 다시 재생합니다.\n"
            "`!loop` - 현재 재생 중인 음악을 반복 재생합니다.\n"
            "`!queue [검색어]` - 검색어로 유튜브 영상을 찾아 큐에 추가합니다.\n"
            "`!show_queue` - 현재 큐에 있는 음악 목록을 보여줍니다.\n"
            "`!skip` - 현재 재생 중인 음악을 건너뜁니다."
        )
        await ctx.send(help_text)

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            await self.join_voice_channel(ctx)
            await self.send_help_message(ctx)
        else:
            await ctx.send("You are not connected to a voice channel.")
            raise commands.CommandError("Author not connected to a voice channel.")

    @commands.command()
    async def play(self, ctx, *, keyword=None):
        if keyword:
            async with ctx.typing():
                videosSearch = VideosSearch(keyword, limit=1)
                result = videosSearch.result()["result"][0]
                url = result["link"]
                title = result["title"]

                self.queue.append((url, title))
                await ctx.send(f"Added to queue: {title}")

                if self.current_index == -1:  # 현재 재생 중인 곡이 없을 때만 재생 시작
                    await self.play_next(ctx)
        else:
            if self.queue:
                await self.play_next(ctx)
            else:
                await ctx.send("Queue is empty.")

    def after_play(self, ctx, error):
        if error:
            print(f"Player error: {error}")
        coro = (
            self.play_next(ctx)
            if not self.loop
            else self.play_url(ctx, self.current_url, "Current Song")
        )
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Error resuming playback: {e}")

    async def play_url(self, ctx, url, title=""):
        try:
            self.current_url = url
            player = await self.create_player(url)
            ctx.voice_client.play(player, after=lambda e: self.after_play(ctx, e))
            await self.send_now_playing(ctx, url, title)
        except Exception as e:
            await ctx.send(f"Error playing URL: {e}")

    async def send_now_playing(self, ctx, url, title):
        videosSearch = VideosSearch(url, limit=1)
        result = videosSearch.result()["result"][0]
        thumbnail = result["thumbnails"][0]["url"]
        channel = result["channel"]["name"]
        views = result["viewCount"]["text"]
        duration = result["duration"]

        embed = discord.Embed(
            title="Now Playing",
            description=f"[{title}]({url})",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=thumbnail)
        embed.add_field(name="Channel", value=channel, inline=True)
        embed.add_field(name="Views", value=views, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="⏯️", style=discord.ButtonStyle.primary, custom_id="pause_resume"
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
        view.add_item(
            discord.ui.Button(
                label="⏭️", style=discord.ButtonStyle.secondary, custom_id="skip"
            )
        )

        await ctx.send(embed=embed, view=view)

    @commands.command()
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()
        self.current_index = -1

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
    async def queue(self, ctx, *, keyword):
        videosSearch = VideosSearch(keyword, limit=1)
        result = videosSearch.result()["result"][0]
        url = result["link"]
        title = result["title"]

        self.queue.append((url, title))
        await ctx.send(f"Added to queue: {title}")

    @commands.command()
    async def show_queue(self, ctx):
        if not self.queue:
            await ctx.send("Queue is empty.")
        else:
            queue_list = "\n".join(
                [
                    f"**재생 중**: **{idx + 1}. {title}**" if idx == self.current_index else f"{idx + 1}. {title}"
                    for idx, (url, title) in enumerate(self.queue)
                ]
            )
            await ctx.send(f"Current queue:\n{queue_list}")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client.is_playing():
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
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        custom_id = interaction.data["custom_id"]
        music_cog = self

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
                await interaction.followup.send("Queue is empty.", ephemeral=True, delete_after=5)
            else:
                queue_list = "\n".join(
                    [
                        f"**{idx + 1}. (재생 중) {title}**" if idx == music_cog.current_index else f"{idx + 1}. {title}"
                        for idx, (url, title) in enumerate(music_cog.queue)
                    ]
                )
                await interaction.followup.send(
                    f"Current queue:\n{queue_list}", ephemeral=True, delete_after=5
                )

        elif custom_id == "skip":
            if interaction.guild.voice_client.is_playing():
                interaction.guild.voice_client.stop()
            else:
                await interaction.response.send_message(
                    "No song is currently playing.", ephemeral=True, delete_after=5
                )


async def setup(bot):
    await bot.add_cog(Music(bot))
