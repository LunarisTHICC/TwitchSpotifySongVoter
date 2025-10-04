# bot.py
import os
import aiohttp
from twitchio.ext import commands

API_BASE = os.getenv("API_BASE", "http://localhost:3000")

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=os.getenv("TWITCH_OAUTH_TOKEN"),
                         prefix="!",
                         initial_channels=[os.getenv("TWITCH_CHANNEL")])

    async def event_ready(self):
        print(f"Logged in as {self.nick}")

    @commands.command(name="interactive")
    async def interactive(self, ctx):
        await ctx.send(f"Vote next track here: {API_BASE}/static/index.html")

    @commands.command(name="vote")
    async def vote(self, ctx):
        query = ctx.message.content[len("!vote "):].strip()
        if not query:
            await ctx.send("Usage: !vote <song/artist/album/playlist>")
            return
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_BASE}/api/vote", json={"query": query}) as resp:
                if resp.status == 200:
                    await ctx.send(f"@{ctx.author.name} your vote was recorded.")
                else:
                    await ctx.send(f"@{ctx.author.name} vote failed.")

    @commands.command(name="queue")
    async def queue(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/api/state") as resp:
                s = await resp.json()
                upcoming = ", ".join(q.get("title","") for q in s.get("queue", [])[:5])
                await ctx.send(upcoming if upcoming else "Queue is empty.")

if __name__ == "__main__":
    Bot().run()