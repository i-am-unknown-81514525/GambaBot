import os

from discord.ext.commands import Cog
from discord import app_commands, Interaction, Embed, Color
from discord.app_commands import allowed_contexts, allowed_installs
from helpers.impersonate import impersonate_user

import aiohttp


class Balance(Cog):
    def __init__(self, bot):
        self.bot = bot

    @allowed_contexts(guilds=True, dms=True, private_channels=True)
    @allowed_installs(guilds=True, users=True)
    @app_commands.command(name="balance", description="Check your account balance and recent transactions.")
    async def check_balance(self, interaction: Interaction):
        await interaction.response.defer()
        jwt = impersonate_user(interaction.user.id)

        async with aiohttp.ClientSession(os.environ["INTERNAL_LINK"], headers={"X-API-KEY": jwt}) as session:
            async with session.get("/user/profile/@me") as response:
                if not response.ok:
                    if response.status == 404:
                        return await interaction.followup.send(embed=Embed(
                            title="No Account Found",
                            description="You don't have an account yet. Use `/create_acc` to get started!",
                            color=Color.red()
                        ))
                    error_details = await response.text()
                    return await interaction.followup.send(embed=Embed(
                        title=f"API Error: {response.status}",
                        description=f"The server is having a moment.\n```{error_details}```",
                        color=Color.red()
                    ))

                data = await response.json()
                balance_data = data.get("balance", {})
                transactions = data.get("transactions", [])

                embed = Embed(
                    title=f"{interaction.user.display_name}'s Wallet",
                    color=Color.green()
                )

                balance_str = "\n".join(f"**{amount}** {name}" for name, amount in balance_data.items())
                if not balance_str:
                    balance_str = "You're broke!"
                embed.add_field(name="💰 Balance", value=balance_str, inline=False)

                tx_str = "\n".join(f"`{tx['tx'][:10]}`" for tx in transactions)
                if not tx_str:
                    tx_str = "No transactions yet."
                embed.add_field(name="📜 Recent Transactions (Last 10)", value=tx_str, inline=False)

                await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Balance(bot))