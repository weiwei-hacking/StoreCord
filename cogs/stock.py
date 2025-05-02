import discord
from discord import app_commands
from discord.ext import commands
import json
import random
from datetime import datetime
import os

def load_prices():
    try:
        with open('configs/price.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stock", description="Show the stock of all txt files")
    async def stock(self, interaction: discord.Interaction):
        stock_dir = 'stock'
        if not os.path.exists(stock_dir):
            await interaction.response.send_message("Stock directory not found!", ephemeral=True)
            return

        txt_files = [f for f in os.listdir(stock_dir) if f.endswith('.txt')]
        if not txt_files:
            await interaction.response.send_message("No txt files found in stock directory!", ephemeral=True)
            return

        stock_info = []
        prices = load_prices()
        for txt_file in txt_files:
            file_path = os.path.join(stock_dir, txt_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            # 提取 price 和 limit，並格式化顯示
            price_data = prices.get(txt_file, None)
            if price_data:
                price = price_data.get('price', 'N/A')
                limit = price_data.get('limit', 'N/A')
                price_display = f"Price: {price}, Maximum: {limit}"
            else:
                price_display = "Price: N/A, Maximum: N/A"
            stock_info.append((txt_file[:-4], len(lines), price_display))

        random_color = discord.Color(random.randint(0, 0xFFFFFF))
        embed = discord.Embed(
            title="Stock Information",
            color=random_color,
            timestamp=datetime.now()
        )
        for file_name, line_count, price_display in stock_info:
            embed.add_field(
                name=file_name,
                value=f"{line_count} stock, {price_display}",
                inline=False
            )
        embed.set_footer(text=f"Queried by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Stock(bot))