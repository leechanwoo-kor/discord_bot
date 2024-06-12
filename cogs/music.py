import asyncio
import discord
from youtubesearchpython import VideosSearch
from discord.ext import commands
from utils.ytdl import YTDLSource
from utils.utils import ellipsis
import discord.ui


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop = False
        self.current = None
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
            await ctx.send("대기열이 비어있습니다.", delete_after=3)

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            await self.join_voice_channel(ctx)
        else:
            await ctx.send("You are not connected to a voice channel.")
            raise commands.CommandError("Author not connected to a voice channel.")

    @commands.command(aliases=["p", "P", "ㅔ"])
    async def play(self, ctx, *, keyword=None):
        if not keyword:
            await ctx.send("키워드를 입력하세요.", delete_after=3)
            await ctx.message.delete()
            return

        async with ctx.typing():
            videosSearch = VideosSearch(keyword, limit=1)
            result = videosSearch.result()["result"][0]
            self.queue.append(result)

            if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                result = self.queue.pop(0)
                await self.play_url(ctx, result)
            elif ctx.voice_client.is_playing():
                await self.send_queue(ctx)
        await ctx.message.delete()

    def after_play(self, ctx, error):
        if error:
            print(f"Player error: {error}")
        coro = (
            self.play_next(ctx) if not self.loop else self.play_url(ctx, self.current)
        )
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Error resuming playback: {e}")

    async def play_url(self, ctx, current):
        try:
            self.current = current
            url = current["link"]
            player = await self.create_player(url)
            ctx.voice_client.play(player, after=lambda e: self.after_play(ctx, e))
            await self.send_now_playing(ctx, current)
        except Exception as e:
            await ctx.send(f"Error playing URL: {e}")

    async def send_now_playing(self, ctx, current):
        url = current["link"]
        title = ellipsis(current["title"])
        thumbnail = current["thumbnails"][0]["url"]
        channel = current["channel"]["name"]
        duration = current["duration"]

        max_title_length = 45
        if len(title) > max_title_length:
            title = title[: max_title_length - 3] + "..."

        play_status = "⏸️" if ctx.voice_client.is_paused() else "▶️"
        loop_status = "Y" if self.loop else "N"

        embed = discord.Embed(
            title=f"{play_status}  Now Playing  💿  | {channel}",
            description=f"[{title}]({url})",
            color=discord.Color.lighter_grey(),
        )
        embed.set_thumbnail(url=thumbnail)
        embed.add_field(name="길이", value=duration, inline=True)
        embed.add_field(name="요청자", value=ctx.author.mention, inline=True)
        embed.add_field(name="반복", value=loop_status, inline=True)

        view = self.create_view()

        if self.now_playing_message:
            await self.now_playing_message.delete()

        self.now_playing_message = await ctx.send(embed=embed, view=view)

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
        if not self.queue:
            embed = discord.Embed(
                description="🎶 대기열이 비어있습니다.",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed, delete_after=3)
        else:
            now = ellipsis(self.current["title"])
            queue_list = "\n".join(
                [
                    f"{idx + 1}. {ellipsis(video['title'], 45)}"
                    for idx, video in enumerate(self.queue)
                ]
            )
            embed = discord.Embed(
                title="🎶 Current Queue",
                description=f"**Now Playing:** {now}\n\n**Up Next:**\n{queue_list}",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed, delete_after=3)

    @commands.command()
    async def volume(self, ctx, volume: int):
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await self.join_voice_channel(ctx)
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")


async def setup(bot):
    await bot.add_cog(Music(bot))
