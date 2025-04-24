import discord
from discord import app_commands
from discord.ext import commands
import os

class Order(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="order", description="View a specific order")
    @app_commands.describe(order_id="Order ID (md5)")
    async def order(self, interaction: discord.Interaction, order_id: str):
        try:
            order_dir = 'order'
            if not os.path.exists(order_dir):
                await interaction.response.send_message("No orders exist currently!", ephemeral=True)
                return

            order_filename = f"{order_id}.txt"
            order_path = os.path.join(order_dir, order_filename)
            if not os.path.exists(order_path):
                await interaction.response.send_message(f"Order '{order_id}' not found!", ephemeral=True)
                return

            discord_file = discord.File(order_path, filename=order_filename)
            try:
                await interaction.user.send(file=discord_file)
                await interaction.response.send_message("Order file has been sent to your DMs!", ephemeral=True)
            except discord.Forbidden:
                discord_file = discord.File(order_path, filename=order_filename)
                await interaction.response.send_message(file=discord_file, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Failed to view order: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Order(bot))