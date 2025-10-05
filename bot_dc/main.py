import asyncio
import logging
from pathlib import Path
from discord.ext import commands
import discord
from dotenv import load_dotenv
import os

load_dotenv()  # pyright: ignore[reportUnusedCallResult]

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

COGS_DIR = Path() / "cogs"

async def load_cogs():
    """Loads all cogs from the cogs directory."""
    for cog_file in COGS_DIR.glob("*.py"):
        if cog_file.stem != "__init__":
            try:
                await bot.load_extension(f"cogs.{cog_file.stem}")
                print(f"Loaded cog: {cog_file.stem}")
            except commands.ExtensionError as e:
                logging.error(f"Failed to load cog {cog_file.stem}", exc_info=e)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await load_cogs()
    print("Cogs loaded")

@bot.command("sync")
async def sync(ctx: commands.Context):
    await bot.tree.sync()
    await ctx.send("Synced")

bot.run(TOKEN)
