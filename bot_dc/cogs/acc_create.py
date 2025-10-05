import os

from discord.ext.commands import Cog, Bot
from discord.ext import commands
from discord import app_commands, Interaction
from discord.app_commands import allowed_contexts, allowed_installs
from helpers.impersonate import impersonate_user

import aiohttp

class CreateAcc(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @allowed_contexts(guilds=True, dms=True, private_channels=True)
    @allowed_installs(guilds=True, users=True)
    @app_commands.command(name="create_acc", description="Create an account")
    async def create_acc(self, interaction: Interaction):
        await interaction.response.defer()
        jwt = impersonate_user(interaction.user.id)
        async with aiohttp.ClientSession(os.environ["INTERNAL_LINK"]) as session:
            async with session.post("/")
        

    

async def setup(bot):
    await bot.add_cog(CreateAcc(bot))