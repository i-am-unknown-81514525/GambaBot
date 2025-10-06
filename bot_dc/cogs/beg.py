import os, random

from discord.ext.commands import Cog, Bot
from discord.ext import commands
from discord import app_commands, Interaction
from discord.app_commands import allowed_contexts, allowed_installs
from helpers.impersonate import impersonate_user
import discord

import aiohttp

class Beg(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @allowed_contexts(guilds=True, dms=True, private_channels=True)
    @allowed_installs(guilds=True, users=True)
    @app_commands.command(name="beg", description="Beg for some money from the system")
    async def create_acc(self, interaction: Interaction, prompt: str):
        _ = prompt # For AI later
        await interaction.response.defer()
        jwt = impersonate_user(interaction.user.id)
        async with aiohttp.ClientSession(os.environ["INTERNAL_LINK"], headers={"X-API-KEY": jwt}) as session:
            async with session.get("/account/list/@me") as req:
                if not req.ok:
                    async with session.get(f"/get/{interaction.user.id}") as req2:
                        if not req2.ok:
                            return await interaction.followup.send(embed=discord.Embed(title="You don't have an account yet", color=discord.Color.red(), description="Create an account with /create_acc"))
                    return await interaction.followup.send(embed=discord.Embed(
                        title="Error",
                        description="Something went wrong",
                        color=discord.Color.red()
                    ))
                accs = await req.json()
                first_acc = accs[0]["id"]
                total_balance = 0
                for acc in accs:
                    total_balance += acc.get("balance",{}).get("0")
                if total_balance < 100:
                    return await interaction.followup.send(embed=discord.Embed(
                        title="You tried...",
                        description="You cannot be begging, you have way too much money, get poor first.",
                        color=discord.Color.red()
                    ))
                if random.randint(1, 5) >= 4:
                    return await interaction.followup.send(embed=discord.Embed(
                        title="You tried...",
                        description="You are deemed not worthy for the prize, try again later.",
                        color=discord.Color.red()
                    ))
                amount = random.randint(1, 100)
                async with session.post(
                    "/transaction/pay", 
                    headers={"X-API-KEY": impersonate_user(0)},
                    json={"src": 0, "dst": first_acc, "coin_id": 0, "amount": amount}
                ) as req:
                    if not req.ok:
                        return await interaction.followup.send(embed=discord.Embed(
                            title="Someone tried to give you money but he couldn't find the wallet",
                            description="So unfortunate, I am so sorry (I am actually not)",
                            color=discord.Color.red()
                        ))
                    return await interaction.followup.send(embed=discord.Embed(
                        title="You got something...",
                        description=f"You are granted {amount} coins for your effort of begging",
                        color=discord.Color.red()
                    ))
        return await interaction.followup.send(embed=discord.Embed(
            title="Error",
            description="Something went wrong",
            color=discord.Color.red()
        ))
        
        


async def setup(bot):
    await bot.add_cog(Beg(bot))