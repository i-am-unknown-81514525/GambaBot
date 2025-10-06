import os
from datetime import datetime

from discord.ext.commands import Cog, Bot
from discord import app_commands, Interaction, Embed, Color
from discord.app_commands import allowed_contexts, allowed_installs

import aiohttp

class Transaction(Cog):
    def __init__(self, bot):
        self.bot = bot

    @allowed_contexts(guilds=True, dms=True, private_channels=True)
    @allowed_installs(guilds=True, users=True)
    @app_commands.command(name="transaction", description="View details of a specific transaction.")
    @app_commands.describe(
        identifier="The ID or TX hash of the transaction to look up."
    )
    async def view_transaction(self, interaction: Interaction, identifier: str):
        await interaction.response.defer()
        async with aiohttp.ClientSession(os.environ['INTERNAL_LINK']) as session:
            async with session.get(f"/transaction/get/{identifier}") as response:
                if not response.ok:
                    if response.status == 404:
                        return await interaction.followup.send(embed=Embed(
                            title="What are you looking for?",
                            description=f"You cannot just magic out a transaction ID `{identifier}` and expect me to give me something useful right?",
                            color=Color.red()
                        ))
                    error_details = await response.text()
                    return await interaction.followup.send(embed=Embed(
                        title=f"API Error: {response.status}",
                        description=f"The server hate you.\n```{error_details}```",
                        color=Color.red()
                    ))

                data = await response.json()

                embed = Embed(
                    title=f"Transaction #{data['id']}",
                    description=f"**Hash:** `{data['tx']}`",
                    color=Color.blue()
                )

                # Format timestamp
                ts = datetime.fromisoformat(data['create_dt']).strftime('%Y-%m-%d %H:%M:%S UTC')
                embed.add_field(name="Timestamp", value=ts, inline=False)

                # Format transfer details
                flow = f"`{data['src']}` → `{data['dst']}`"
                embed.add_field(name="Flow", value=flow, inline=True)
                embed.add_field(name="Amount", value=f"{data['amount']} {data['coin_read_name']}", inline=True)
                embed.add_field(name="Type", value=data['kind'].capitalize(), inline=True)

                if data.get('reason'):
                    embed.add_field(name="Reason", value=data['reason'], inline=False)

                # Add game-specific details
                if data.get('game'):
                    game_info = data['game']
                    result = "Win" if game_info['user_win'] else "Loss"
                    embed.add_field(name="Game Result", value=result, inline=True)
                    embed.add_field(name="Server Secret", value=f"```{game_info['server_secret'][:1018]}```", inline=False)
                    embed.add_field(name="Client Secret", value=f"```{game_info['client_secret'][:1018]}```", inline=False)

                await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Transaction(bot))