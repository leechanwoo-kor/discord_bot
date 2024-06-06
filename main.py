import asyncio
import discord
from youtubesearchpython import VideosSearch
from discord.ext import commands
from config import Token
from utils.ytdl import YTDLSource
import discord.ui
from discord import InteractionType


# 음악 재생 클래스. 커맨드 포함.
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop = False  # 루프 상태 저장 변수 추가
        self.current_url = None  # 현재 재생 중인 URL 저장

    @commands.command()
    async def join(self, ctx):
        """Joins a voice channel"""

        channel = ctx.author.voice.channel

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def play(self, ctx, *, keyword):
        """Stream music from youtube"""

        async with ctx.typing():
            videosSearch = VideosSearch(keyword, limit=1)
            result = videosSearch.result()["result"][0]
            url = result["link"]
            title = result["title"]
            thumbnail = result["thumbnails"][0]["url"]
            channel = result["channel"]["name"]
            views = result["viewCount"]["text"]
            duration = result["duration"]

            self.current_url = url  # 현재 재생 중인 URL 저장

            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: self.after_play(ctx, e))

        embed = discord.Embed(
            title="Now Playing",
            description=f"[{title}]({url})",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=thumbnail)
        embed.add_field(name="Channel", value=channel, inline=True)
        embed.add_field(name="Views", value=views, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)

        # 버튼을 포함하는 View 생성
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="⏯️",
                style=discord.ButtonStyle.primary,
                custom_id="pause_resume",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="🔁",
                style=discord.ButtonStyle.secondary,
                custom_id="toggle_loop",
            )
        )

        await ctx.send(embed=embed, view=view)

    def after_play(self, ctx, error):
        if error:
            print(f"Player error: {error}")
        if self.loop and self.current_url:
            coro = self.play_url(ctx, self.current_url)
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error resuming playback: {e}")

    async def play_url(self, ctx, url):
        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: self.after_play(ctx, e))

    @commands.command()
    async def url(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            self.current_url = url  # 현재 재생 중인 URL 저장
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: self.after_play(ctx, e))

        await ctx.send(f"Now playing: {player.title}")

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @commands.command()
    async def pause(self, ctx):
        """음악을 일시정지 할 수 있습니다."""

        if ctx.voice_client.is_paused() or not ctx.voice_client.is_playing():
            return await ctx.send(
                "음악이 이미 일시 정지 중이거나 재생 중이지 않습니다."
            )

        ctx.voice_client.pause()

    @commands.command()
    async def resume(self, ctx):
        """일시정지된 음악을 다시 재생할 수 있습니다."""

        if ctx.voice_client.is_playing() or not ctx.voice_client.is_paused():
            return await ctx.send(
                "음악이 이미 재생 중이거나 재생할 음악이 존재하지 않습니다."
            )

        ctx.voice_client.resume()

    @commands.command()
    async def loop(self, ctx):
        """Toggles loop on/off"""

        self.loop = not self.loop
        await ctx.send(f"Loop is now {'enabled' if self.loop else 'disabled'}.")

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="Relatively simple music bot example",
    intents=intents,
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


# 인터랙션 핸들러 등록
@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
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
            music_cog = bot.get_cog("Music")
            music_cog.loop = not music_cog.loop
            await interaction.response.send_message(
                f"Loop is now {'enabled' if music_cog.loop else 'disabled'}.",
                ephemeral=True,
                delete_after=5,
            )


async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(Token)


asyncio.run(main())
