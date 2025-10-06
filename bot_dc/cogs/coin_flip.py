import os, secrets
from typing import Optional

from discord.ext.commands import Cog, Bot
from discord.ext import commands
from discord import app_commands, Interaction
from discord.app_commands import allowed_contexts, allowed_installs
from helpers.impersonate import impersonate_user
import discord

import aiohttp

class CoinFlip(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @allowed_contexts(guilds=True, dms=True, private_channels=True)
    @allowed_installs(guilds=True, users=True)
    @app_commands.command(name="coinflip", description="Flip a coin to win or lose money.")
    @app_commands.describe(
        side="The side of the coin you are betting on.",
        amount="The amount of money you want to bet."
    )
    @app_commands.choices(side=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails"),
    ])
    async def coinflip(self, interaction: Interaction, side: app_commands.Choice[str], amount: app_commands.Range[int, 1], client_secret: Optional[str] = None):
        await interaction.response.defer()
        jwt = impersonate_user(interaction.user.id)
        
        async with aiohttp.ClientSession(os.environ["INTERNAL_LINK"], headers={"X-API-KEY": jwt}) as session:
            async with session.post("/game/init") as init_resp:
                if not init_resp.ok:
                    if init_resp.status == 404:
                         return await interaction.followup.send(embed=discord.Embed(title="You don't have an account yet", color=discord.Color.red(), description="Create an account with `/create_acc` first!"))
                    return await interaction.followup.send(embed=discord.Embed(title="Error", description="Could not start a game because the server hate you", color=discord.Color.red()))
                game_data = await init_resp.json()
                game_id = game_data["game_id"]
            if not client_secret:
                client_secret = secrets.token_hex(32)
            payload = {
                "client_secret": client_secret,
                "amount": amount,
                "coin_id": 0, 
                "side": side.value == "heads" # True for heads, False for tails
            }

            async with session.post(f"/game/play_coinflip/{game_id}", json=payload) as play_resp:
                if play_resp.ok:
                    play_data = await play_resp.json()
                    win = play_data["win"]
                    net_delta = play_data["user_net_delta"]

                    if win:
                        embed = discord.Embed(
                            title="You Won?",
                            description=f"That's impossible, we make sure to rigged the game so you cannot win\n-# The coin landed on **{side.name}**. You won **{net_delta}** coins!",
                            color=discord.Color.green()
                        )
                    else:
                        embed = discord.Embed(
                            title="You Lost.",
                            description=f"(Really what do you expected)\n-# The coin landed on the other side. You lost **{abs(net_delta)}** coins.",
                            color=discord.Color.red()
                        )
                    
                    tx_id = play_data.get("transaction", {}).get("tx")
                    if tx_id:
                        embed.set_footer(text=f"TX: {tx_id}")

                    return await interaction.followup.send(embed=embed)
                
                if play_resp.status == 422:
                    return await interaction.followup.send(embed=discord.Embed(
                        title="You cannot be spending that much", 
                        description=f"Our intelligence agent has identified and prevented you from overdrafting because they do not " 
                        "believe you can pay back the **{amount}** coins that you are trying to gamble.", color=discord.Color.orange()))
                
                error_details = await play_resp.text()
                return await interaction.followup.send(
                    embed=discord.Embed(
                        title=f"Error: {play_resp.status}", 
                        description=f"An unexpected error occurred(The server hate you).\n```{error_details}```", 
                        color=discord.Color.red()
                    )
                )

async def setup(bot):
    await bot.add_cog(CoinFlip(bot))