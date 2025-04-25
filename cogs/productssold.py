import discord
from discord import app_commands
from discord.ext import commands
import os
import random

class ProductsSold(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="productssold", description="Show the total sold amount of each product in the order")
    async def productssold(self, interaction: discord.Interaction):
        # Check if the order folder exists
        order_dir = 'order'
        if not os.path.exists(order_dir):
            await interaction.response.send_message("Order folder not found!", ephemeral=True)
            return

        # Get all txt files
        txt_files = [f for f in os.listdir(order_dir) if f.endswith('.txt')]
        if not txt_files:
            await interaction.response.send_message("No txt files found in the order folder!", ephemeral=True)
            return

        # Initialize a dictionary to store product totals
        product_totals = {}
        skipped_files = []

        # Extract data from each file
        for txt_file in txt_files:
            file_path = os.path.join(order_dir, txt_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines()]
                
                # Ensure the file has at least 7 lines
                if len(lines) < 7:
                    print(f"File {txt_file} has incorrect format, skipping")
                    skipped_files.append(txt_file)
                    continue

                # Extract Product name and Amount
                product_name = lines[4].split(':', 1)[1].strip() if ':' in lines[4] else lines[4]
                amount_str = lines[5].split(':', 1)[1].strip() if ':' in lines[5] else lines[5]

                # Convert Amount to integer
                amount = int(amount_str)

                # Add to product totals
                if product_name in product_totals:
                    product_totals[product_name] += amount
                else:
                    product_totals[product_name] = amount

            except Exception as e:
                print(f"Error processing file {txt_file}: {e}")
                skipped_files.append(txt_file)
                continue

        # Check if there is any data
        if not product_totals:
            message = "No valid product data found!"
            if skipped_files:
                message += f"\nSkipped files due to errors: {', '.join(skipped_files)}"
            await interaction.response.send_message(message, ephemeral=True)
            return

        # Create embed with random color
        random_color = discord.Color(random.randint(0, 0xFFFFFF))
        embed = discord.Embed(
            title="Products Sold Statistics",
            color=random_color,
            timestamp=discord.utils.utcnow()
        )

        # Add fields for each product
        for product_name, total_amount in product_totals.items():
            embed.add_field(
                name=product_name,
                value=f"{total_amount}",
                inline=False
            )

        embed.set_footer(text=f"Queried by {interaction.user.display_name}")

        # Send the embed
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ProductsSold(bot))