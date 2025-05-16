import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import string
import hashlib
import time

last_purchase_times = {}

def load_balances():
    try:
        with open('configs/balance.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {user_id: int(balance) for user_id, balance in data.items()}
    except Exception as e:
        return {}

def save_balances(balances):
    try:
        with open('configs/balance.json', 'w', encoding='utf-8') as f:
            json.dump(balances, f, indent=4, ensure_ascii=False)
    except Exception as e:
        pass

def load_prices():
    try:
        with open('configs/price.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for product, details in data.items():
                data[product]['price'] = int(details['price'])
                if details.get('limit') is not None:
                    data[product]['limit'] = int(details['limit'])
            return data
    except Exception as e:
        return {}

def load_configs():
    try:
        with open('configs/normal.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'cooldown' in data and data['cooldown'] is not None:
                data['cooldown'] = int(data['cooldown'])
            return data
    except Exception as e:
        return {}

def load_permissions():
    try:
        with open('configs/permissions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"users": [], "roles": []}

class Purchase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="purchase", description="Purchase products")
    @app_commands.describe(amount="Number of products to purchase")
    async def purchase(self, interaction: discord.Interaction, amount: int):
        try:
            configs = load_configs()
            cooldown = configs.get('cooldown')
            user_id_str = str(interaction.user.id)
            current_time = time.time()

            if cooldown is not None and cooldown > 0:
                last_purchase = last_purchase_times.get(user_id_str, 0)
                time_since_last_purchase = current_time - last_purchase
                if time_since_last_purchase < cooldown:
                    remaining_time = int(cooldown - time_since_last_purchase)
                    await interaction.response.send_message(f"Please wait {remaining_time} seconds before using this command again!", ephemeral=True)
                    return
                last_purchase_times[user_id_str] = current_time

            if amount <= 0:
                await interaction.response.send_message("Purchase quantity must be a positive number!", ephemeral=True)
                return

            balances = load_balances()
            user_balance = balances.get(user_id_str, 0)

# 檢查產品價格並計算最低價格
            prices = load_prices()
            if not prices:
                await interaction.response.send_message("No products available for purchase currently!", ephemeral=True)
                return

            min_price = float('inf')
            for product_data in prices.values():
                price = product_data.get('price', float('inf'))
                if price < min_price:
                    min_price = price

            # 如果最低價格無限大，說明沒有有效產品價格
            if min_price == float('inf'):
                await interaction.response.send_message("No valid product prices available!", ephemeral=True)
                return

            balances = load_balances()
            user_id_str = str(interaction.user.id)
            user_balance = balances.get(user_id_str, 0)

            # 檢查用戶積分是否足夠購買最低價格的產品
            if user_balance < min_price:
                await interaction.response.send_message("Insufficient credits to purchase any product!", ephemeral=True)
                return

            # 檢查用戶是否能負擔指定數量的產品
            affordable_products = {}
            for product_file, product_data in prices.items():
                price = product_data.get('price', 0)
                total_cost = price * amount
                if user_balance >= total_cost:
                    affordable_products[product_file] = (price, total_cost)

            if not affordable_products:
                await interaction.response.send_message("Your credits are insufficient to purchase the requested quantity!", ephemeral=True)
                return

            # 檢查庫存
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
                def __init__(self, products, amount, bot):
                    options = [
                        discord.SelectOption(
                            label=f"{name}",
                            value=f"{name}|{price}|{total_cost}",
                            description=f"Price: {total_cost} ({price} credits/unit)"
                        ) for name, price, total_cost in products
                    ]
                    super().__init__(placeholder="Select a product...", options=options, min_values=1, max_values=1)
                    self.amount = amount
                    self.bot = bot

                async def callback(self, interaction: discord.Interaction):
                    try:
                        selected = self.values[0].split('|')
                        product_name = selected[0]
                        price = int(selected[1])
                        total_cost = int(selected[2])

                        product_file = f"{product_name}.txt"
                        product_data = prices.get(product_file, {})
                        purchase_limit = product_data.get('limit')
                        if purchase_limit is not None and self.amount > purchase_limit:
                            await interaction.response.send_message(
                                f"The product '{product_name}' has a purchase limit of {purchase_limit} units per transaction, but you attempted to purchase {self.amount} units!",
                                ephemeral=True
                            )

                            configs = load_configs()
                            limit_alert_id = configs.get('limit_alert')
                            if limit_alert_id:
                                try:
                                    alert_channel = self.bot.get_channel(int(limit_alert_id))
                                    if alert_channel:
                                        permissions = load_permissions()
                                        mentions = []
                                        for user_id in permissions.get('users', []):
                                            mentions.append(f"<@{user_id}>")
                                        for role_id in permissions.get('roles', []):
                                            mentions.append(f"<@&{role_id}>")
                                        mention_str = " ".join(mentions) if mentions else "No designated personnel"
                                        current_time = int(discord.utils.utcnow().timestamp())
                                        embed = discord.Embed(
                                            description=(
                                                f"{interaction.user.mention} attempted to purchase `{product_name}` **x{self.amount}**, "
                                                f"but exceeded the limit of {purchase_limit} units!\n"
                                                f"Time: <t:{current_time}:F>"
                                            ),
                                            color=discord.Color.red(),
                                            timestamp=discord.utils.utcnow()
                                        )
                                        embed.set_footer(text="Purchase Limit Warning")
                                        await alert_channel.send(content=mention_str, embed=embed)
                                except ValueError:
                                    pass
                            return

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
                                # 編輯原始訊息並移除按鈕
                                await interaction.response.edit_message(
                                    content="Processing your purchase...", 
                                    view=None
                                )
                                self.stop()

                            @discord.ui.button(label="No", style=discord.ButtonStyle.red)
                            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                                self.value = False
                                # 編輯原始訊息並移除按鈕
                                await interaction.response.edit_message(
                                    content="Purchase canceled.", 
                                    view=None
                                )
                                self.stop()

                        view = ConfirmView(interaction, product_name, price, total_cost, self.amount)
                        await interaction.response.send_message(
                            f"Are you sure you want to purchase {self.amount} {product_name} for a total of {total_cost} credits?",
                            view=view,
                            ephemeral=True
                        )
                        await view.wait()

                        if view.value is None or not view.value:
                            return  # 超時或取消已由按鈕處理

                        # 繼續處理購買邏輯
                        balances = load_balances()
                        user_id_str = str(interaction.user.id)
                        user_balance = balances.get(user_id_str, 0)
                        if user_balance < total_cost:
                            await interaction.edit_original_response(
                                content="Your credits are insufficient to complete this purchase!", 
                                view=None
                            )
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
                            await interaction.edit_original_response(
                                content="Order file has been sent to your DMs!", 
                                view=None
                            )
                        except discord.Forbidden:
                            discord_file = discord.File(order_path, filename=order_filename)
                            await interaction.edit_original_response(
                                content="Order file sent below:", 
                                file=discord_file, 
                                view=None
                            )
                    except Exception as e:
                        await interaction.edit_original_response(
                            content=f"Error during purchase process: {e}", 
                            view=None
                        )

                        try:
                            configs = load_configs()
                            public_logs_id = configs.get('public_logs')
                            private_logs_id = configs.get('private_logs')

                            current_time = int(discord.utils.utcnow().timestamp())

                            if public_logs_id:
                                try:
                                    public_channel = self.bot.get_channel(int(public_logs_id))
                                    if public_channel:
                                        permissions = public_channel.permissions_for(public_channel.guild.me)
                                        if permissions.send_messages:
                                            embed = discord.Embed(
                                                description=f"Someone purchased `{product_name}` **x{self.amount}** with *{total_cost} credits* at <t:{current_time}:R>",
                                                color=discord.Color.gold(),
                                                timestamp=discord.utils.utcnow()
                                            )
                                            embed.set_footer(text="Purchase Completed")
                                            await public_channel.send(embed=embed)
                                except ValueError:
                                    pass

                            if private_logs_id:
                                try:
                                    private_channel = self.bot.get_channel(int(private_logs_id))
                                    if private_channel:
                                        permissions = private_channel.permissions_for(private_channel.guild.me)
                                        if permissions.send_messages:
                                            embed = discord.Embed(
                                                description=(
                                                    f"{interaction.user.mention} purchased `{product_name}` **x{self.amount}** with *{total_cost} credits* at <t:{current_time}:T>\n"
                                                    f"New balance: {balances[user_id_str]} | Order ID: ||{order_id}||"
                                                ),
                                                color=discord.Color.yellow(),
                                                timestamp=discord.utils.utcnow()
                                            )
                                            embed.set_footer(text="Purchase Completed")
                                            await private_channel.send(embed=embed)
                                except ValueError:
                                    pass
                        except Exception:
                            pass

                    except Exception as e:
                        await interaction.followup.send(f"Error during purchase process: {e}", ephemeral=True)

            view = discord.ui.View()
            view.add_item(ProductSelect(available_products, amount, self.bot))
            await interaction.response.send_message("Please select a product to purchase:", view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error during purchase process: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Purchase(bot))