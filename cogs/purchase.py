import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import string
import hashlib
import time

def load_balances():
    try:
        with open('configs/balance.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading balance.json: {e}")
        return {}

def save_balances(balances):
    try:
        with open('configs/balance.json', 'w', encoding='utf-8') as f:
            json.dump(balances, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving balance.json: {e}")

def load_prices():
    try:
        with open('configs/price.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading price.json: {e}")
        return {}

class Purchase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="purchase", description="Purchase products")
    @app_commands.describe(amount="Number of products to purchase")
    async def purchase(self, interaction: discord.Interaction, amount: int):
        try:
            if amount <= 0:
                await interaction.response.send_message("Purchase quantity must be a positive number!", ephemeral=True)
                return

            balances = load_balances()
            user_id_str = str(interaction.user.id)
            user_balance = balances.get(user_id_str, 0)

            prices = load_prices()
            if not prices:
                await interaction.response.send_message("No products available for purchase currently!", ephemeral=True)
                return

            min_price = float('inf')
            for price in prices.values():
                if price < min_price:
                    min_price = price
            if user_balance < min_price:
                await interaction.response.send_message("Insufficient credits to purchase any product!", ephemeral=True)
                return

            affordable_products = {}
            for product_file, price in prices.items():
                total_cost = price * amount
                if user_balance >= total_cost:
                    affordable_products[product_file] = (price, total_cost)

            if not affordable_products:
                await interaction.response.send_message("Your credits are insufficient to purchase any product!", ephemeral=True)
                return

            stock_dir = 'stock'
            if not os.path.exists(stock_dir):
                await interaction.response.send_message("No product stock available currently!", ephemeral=True)
                return

            available_products = []
            for product_file, (price, total_cost) in affordable_products.items():
                product_path = os.path.join(stock_dir, product_file)
                if not os.path.exists(product_path):
                    continue
                with open(product_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                if len(lines) >= amount:
                    product_name = product_file.replace('.txt', '')
                    available_products.append((product_name, price, total_cost))

            if not available_products:
                await interaction.response.send_message(f"No products with stock greater than or equal to {amount}!", ephemeral=True)
                return

            class ProductSelect(discord.ui.Select):
                def __init__(self, products, amount):
                    options = [
                        discord.SelectOption(
                            label=f"{name}",
                            value=f"{name}|{price}|{total_cost}",
                            description=f"Price: {total_cost} ({price} credit/per)"
                        ) for name, price, total_cost in products
                    ]
                    super().__init__(placeholder="Select a product...", options=options, min_values=1, max_values=1)
                    self.amount = amount

                async def callback(self, interaction: discord.Interaction):
                    selected = self.values[0].split('|')
                    product_name = selected[0]
                    price = int(selected[1])
                    total_cost = int(selected[2])

                    class ConfirmView(discord.ui.View):
                        def __init__(self, interaction, product_name, price, total_cost, amount):
                            super().__init__(timeout=60)
                            self.interaction = interaction
                            self.product_name = product_name
                            self.price = price
                            self.total_cost = total_cost
                            self.amount = amount
                            self.value = None

                        @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
                        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                            self.value = True
                            self.stop()

                        @discord.ui.button(label="No", style=discord.ButtonStyle.red)
                        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                            self.value = False
                            self.stop()

                    view = ConfirmView(interaction, product_name, price, total_cost, self.amount)
                    await interaction.response.send_message(
                        f"Are you sure you want to purchase {self.amount} {product_name} for a total of {total_cost} credits?",
                        view=view,
                        ephemeral=True
                    )
                    await view.wait()

                    if view.value is None:
                        await interaction.followup.send("Operation timed out, purchase canceled.", ephemeral=True)
                        return
                    if not view.value:
                        await interaction.followup.send("Purchase canceled.", ephemeral=True)
                        return

                    balances = load_balances()
                    user_id_str = str(interaction.user.id)
                    user_balance = balances.get(user_id_str, 0)
                    if user_balance < total_cost:
                        await interaction.followup.send("Your credits are insufficient to complete the purchase!", ephemeral=True)
                        return
                    balances[user_id_str] = user_balance - total_cost
                    save_balances(balances)

                    product_file = os.path.join('stock', f"{product_name}.txt")
                    with open(product_file, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f if line.strip()]
                    selected_lines = random.sample(lines, self.amount)
                    remaining_lines = [line for line in lines if line not in selected_lines]
                    with open(product_file, 'w', encoding='utf-8') as f:
                        if remaining_lines:
                            f.write('\n'.join(remaining_lines))
                        else:
                            f.write('')

                    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    raw_filename = f"{interaction.user.id}{random_str}"
                    order_id = hashlib.md5(raw_filename.encode()).hexdigest()
                    order_filename = f"{order_id}.txt"

                    order_dir = 'order'
                    if not os.path.exists(order_dir):
                        os.makedirs(order_dir)
                    order_path = os.path.join(order_dir, order_filename)

                    order_time = int(time.time())
                    order_content = (
                        f"Order ID: {order_id}\n"
                        f"Order Time: {order_time}\n"
                        f"Order By: {interaction.user.id}\n\n"
                        f"Product name: {product_name}\n"
                        f"Amount: {self.amount}\n"
                        f"Price: {total_cost}\n\n"
                    )
                    for i, line in enumerate(selected_lines):
                        order_content += f"> {line}\n"
                        if i < len(selected_lines) - 1:
                            order_content += "\n"

                    with open(order_path, 'w', encoding='utf-8') as f:
                        f.write(order_content)

                    discord_file = discord.File(order_path, filename=order_filename)
                    try:
                        await interaction.user.send(file=discord_file)
                        await interaction.followup.send("Order file has been sent to your DMs!", ephemeral=True)
                    except discord.Forbidden:
                        discord_file = discord.File(order_path, filename=order_filename)
                        await interaction.followup.send(file=discord_file, ephemeral=True)

            view = discord.ui.View()
            view.add_item(ProductSelect(available_products, amount))
            await interaction.response.send_message("Please select a product to purchase:", view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error during purchase process: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Purchase(bot))
