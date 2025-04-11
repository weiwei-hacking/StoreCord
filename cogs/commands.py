import logging
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import string
import py7zr
import tempfile
import zipfile
import rarfile
import shutil
import hashlib
import time

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        print(f"Initial config loaded: {self.config}")

        # 获取 creditkey 文件夹内的选项
        self.creditkey_options = []
        if os.path.exists('creditkey'):
            self.creditkey_options.extend([f[:-4] for f in os.listdir('creditkey') if f.endswith('.txt')])
        print(f"Loaded creditkey options: {self.creditkey_options}")
        
        self.stock_options = []
        if os.path.exists('stock/file'):
            self.stock_options.extend([f for f in os.listdir('stock/file') if os.path.isdir(os.path.join('stock/file', f))])
        if os.path.exists('stock/text'):
            txt_files = [f[:-4] for f in os.listdir('stock/text') if f.endswith('.txt')]
            self.stock_options.extend(txt_files)
        print(f"Loaded stock options: {self.stock_options}")

    def load_config(self):
        try:
            with open('configs.json', 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Failed to load configs.json: {e}")
            return {"owner": "", "staff": ""}

    # 检查权限
    def check_permission(self, interaction: discord.Interaction) -> bool:
        self.config = self.load_config()
        user_id = str(interaction.user.id)
        owner_id = self.config.get('owner', '')
        staff_id = self.config.get('staff', '')
        print(f"Checking permission for user: {user_id}, owner: {owner_id}, staff: {staff_id}")

        if owner_id and user_id == owner_id:
            print(f"Permission granted: User {user_id} matches owner {owner_id}")
            return True

        if staff_id and isinstance(interaction.user, discord.Member):
            try:
                staff_role_id = int(staff_id)
                has_role = any(role.id == staff_role_id for role in interaction.user.roles)
                if has_role:
                    print(f"Permission granted: User {user_id} has staff role {staff_role_id}")
                    return True
                else:
                    print(f"Permission denied: User {user_id} does not have staff role {staff_role_id}")
            except ValueError:
                print(f"Invalid staff role ID: {staff_id}")
                return False

        print(f"Permission denied: User {user_id} is neither owner nor staff")
        return False

    def update_stock_options(self):
            self.stock_options = []
            file_dir = 'stock/file'
            text_dir = 'stock/text'
            
            if os.path.exists(file_dir):
                folders = [f for f in os.listdir(file_dir) if os.path.isdir(os.path.join(file_dir, f))]
                self.stock_options.extend(folders)
            
            if os.path.exists(text_dir):
                txt_files = [f[:-4] for f in os.listdir(text_dir) if f.endswith('.txt') and not f.startswith('.')]
                self.stock_options.extend(txt_files)


    # 生成 12 位随机码
    def generate_key(self):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(12))

    class Product(app_commands.Group):
        
        @app_commands.command(name="add", description="Add new product to store")
        @app_commands.describe(
            type="Stock type",
            name="Set product name",
            price="Price (per stock how much credit)"
        )
        @app_commands.choices(type=[
            app_commands.Choice(name="file", value="file"),
            app_commands.Choice(name="text", value="text")
        ])
        async def add(self, interaction: discord.Interaction, type: str, name: str, price: int):
            cog = interaction.client.get_cog('Commands')
            if not cog.check_permission(interaction):
                embed = discord.Embed(title="WARNING!", description="You are not allowed to use this command", color=discord.Color.red())
                await interaction.response.send_message(embed=embed)
                return

            if not name or any(c in name for c in r'<>:"/\|?*'):
                embed = discord.Embed(title="WARNING!", description="Your product name is no allow", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if price <= 0:
                embed = discord.Embed(title="WARNING!", description="Your product price need positive integer", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            try:
                if type == "file":
                    target_path = f'stock/file/{name}'
                    if os.path.exists(target_path):
                        embed = discord.Embed(title="WARNING!", description=f"name **{name}** already exists in this product type", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    os.makedirs(target_path)
                
                elif type == "text":
                    target_path = f'stock/text/{name}.txt'
                    if os.path.exists(target_path):
                        embed = discord.Embed(title="WARNING!", description=f"name **{name}** already exists in this product type", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write('')
                
                else:
                    embed = discord.Embed(title="WARNING!", description=f"Invalid stock type!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                credit_data = {}
                if os.path.exists('credit.json'):
                    with open('credit.json', 'r', encoding='utf-8') as f:
                        try:
                            credit_data = json.load(f)
                        except json.JSONDecodeError:
                            credit_data = {}
                
                credit_data[name] = price
                with open('credit.json', 'w', encoding='utf-8') as f:
                    json.dump(credit_data, f, indent=4, ensure_ascii=False)

                embed = discord.Embed(title="SUCCESS!", description=f"Added product **{name}** in {type} with {price} credit", color=discord.Color.green())
                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

        @app_commands.command(name="remove", description="Remove existing products")
        @app_commands.describe(
            name="Product name (will auto scan)"
        )
        async def remove(self, interaction: discord.Interaction, name: str):
            cog = interaction.client.get_cog('Commands')
            if not cog.check_permission(interaction):
                embed = discord.Embed(title="WARNING!", description="You are not allowed to use this command", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            try:
                file_path = f'stock/file/{name}'
                text_path = f'stock/text/{name}.txt'

                if os.path.exists(file_path) and os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                
                elif os.path.exists(text_path):
                    os.remove(text_path)
                
                else:
                    embed = discord.Embed(title="WARNING!", description=f"Product {name} does not exist", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                credit_data = {}
                if os.path.exists('credit.json'):
                    with open('credit.json', 'r', encoding='utf-8') as f:
                        try:
                            credit_data = json.load(f)
                        except json.JSONDecodeError:
                            credit_data = {}
                
                if name in credit_data:
                    del credit_data[name]
                    with open('credit.json', 'w', encoding='utf-8') as f:
                        json.dump(credit_data, f, indent=4, ensure_ascii=False)
                
                embed = discord.Embed(title="SUCCESS!", description=f"Removed product **{name}**", color=discord.Color.green())
                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

        @app_commands.command(name="list", description="Show all product")
        async def list(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog('Commands')
            if not cog.check_permission(interaction):
                embed = discord.Embed(title="WARNING!", description="You are not allowed to use this command", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            try:
                credit_data = {}
                if os.path.exists('credit.json'):
                    with open('credit.json', 'r', encoding='utf-8') as f:
                        try:
                            credit_data = json.load(f)
                        except json.JSONDecodeError:
                            credit_data = {}

                file_products = []
                if os.path.exists('stock/file'):
                    file_products = [f for f in os.listdir('stock/file') if os.path.isdir(os.path.join('stock/file', f))]

                text_products = []
                if os.path.exists('stock/text'):
                    text_products = [f[:-4] for f in os.listdir('stock/text') if f.endswith('.txt')]

                embed = discord.Embed(title="Product list", color=discord.Color.blue())

                if file_products:
                    file_list = "\n".join(
                        f"- {name}: {credit_data.get(name, 'Not priced yet')} credit"
                        for name in sorted(file_products)
                    )
                    embed.add_field(name="File type", value=file_list, inline=False)
                
                if text_products:
                    text_list = "\n".join(
                        f"- {name}: {credit_data.get(name, 'Not priced yet')} credit"
                        for name in sorted(text_products)
                    )
                    embed.add_field(name="Text type", value=text_list, inline=False)

                if not file_products and not text_products:
                    embed.description = "There are currently no products!"

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

        @remove.autocomplete('name')
        async def remove_autocomplete(self, interaction: discord.Interaction, current: str):
            options = []
            if os.path.exists('stock/file'):
                options.extend([f for f in os.listdir('stock/file') if os.path.isdir(os.path.join('stock/file', f))])
            if os.path.exists('stock/text'):
                options.extend([f[:-4] for f in os.listdir('stock/text') if f.endswith('.txt')])
            
            choices = [
                app_commands.Choice(name=option, value=option)
                for option in options
                if current.lower() in option.lower()
            ][:25]
            return choices
                
    @app_commands.command(name="restock", description="Just restock XD")
    @app_commands.describe(
        stock_name="Choose product",
        attachment="Please upload file (.txt .zip .7z .rar)"
    )
    async def restock(self, interaction: discord.Interaction, 
                    stock_name: str,
                    attachment: discord.Attachment):
        if not self.check_permission(interaction):
            embed = discord.Embed(title="WARNING!", description="You are not allowed to use this command", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if stock_name not in self.stock_options:
            embed = discord.Embed(title="WARNING!", description=f"Invalid product name", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            file_dir = 'stock/file'
            text_dir = 'stock/text'

            if stock_name in [f for f in os.listdir(file_dir) if os.path.isdir(os.path.join(file_dir, f))]:
                target_dir = os.path.join(file_dir, stock_name)
                os.makedirs(target_dir, exist_ok=True)

                if attachment.filename.lower().endswith(('.zip', '.rar', '.7z')):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_file = os.path.join(temp_dir, attachment.filename)
                        await attachment.save(temp_file)

                        extracted_count = 0
                        try:
                            if attachment.filename.lower().endswith('.zip'):
                                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                                    zip_ref.extractall(target_dir)
                                    extracted_count = len(zip_ref.namelist())

                            elif attachment.filename.lower().endswith('.rar'):
                                with rarfile.RarFile(temp_file, 'r') as rar_ref:
                                    rar_ref.extractall(target_dir)
                                    extracted_count = len(rar_ref.namelist())

                            elif attachment.filename.lower().endswith('.7z'):
                                with py7zr.SevenZipFile(temp_file, 'r') as seven_zip:
                                    seven_zip.extractall(target_dir)
                                    extracted_count = len(seven_zip.getnames())

                            self.update_stock_options()
                            embed = discord.Embed(title="SUCCESS!", description=f"Added {extracted_count} stock to **{stock_name}**", color=discord.Color.green())
                            await interaction.response.send_message(embed=embed)

                        except Exception as e:
                            embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                            return
                
                else:
                    file_path = os.path.join(target_dir, attachment.filename)
                    await attachment.save(file_path)
                    self.update_stock_options()
                    embed = discord.Embed(title="SUCCESS!", description=f"Added {extracted_count} stock to **{stock_name}**", color=discord.Color.green())
                    await interaction.response.send_message(embed=embed)
            
            elif os.path.exists(os.path.join(text_dir, f'{stock_name}.txt')):
                file_path = os.path.join(text_dir, f'{stock_name}.txt')
                content = await attachment.read()
                content_str = content.decode('utf-8')
                new_lines = len([line for line in content_str.splitlines() if line.strip()])
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + content_str)
                self.update_stock_options()
                embed = discord.Embed(title="SUCCESS!", description=f"Added {new_lines} stock to **{stock_name}**", color=discord.Color.green())
                await interaction.response.send_message(embed=embed)

            else:
                embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @restock.autocomplete('stock_name')
    async def restock_autocomplete(self, interaction: discord.Interaction, current: str):
        self.update_stock_options()
        choices = [
            app_commands.Choice(name=option, value=option)
            for option in self.stock_options
            if current.lower() in option.lower()
        ][:25]
        return choices

    @app_commands.command(name="creditkey", description="Manager credit redeem key")
    @app_commands.describe(
        action="choose add or remove or show",
        key_type="how much credit",
        amount="Add how much key (only add)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove"),
        app_commands.Choice(name="show", value="show")
    ])
    async def creditkey(self, interaction: discord.Interaction, 
                       action: str, 
                       key_type: str, 
                       amount: int = None):
        if not self.check_permission(interaction):
            embed = discord.Embed(title="WARNING!", description="You are not allowed to use this command", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if key_type not in self.creditkey_options:
            embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        file_path = f'creditkey/{key_type}.txt'

        if action == "add":
            if amount is None or amount <= 0:
                embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            try:
                if key_type == "custom":
                    # 自定义兑换码：生成 1 个 {随机码}.{积分值}
                    key = f"{self.generate_key()}.{amount}"
                    count = 1
                else:
                    # 标准兑换码：生成 amount 个随机码
                    key = [self.generate_key() for _ in range(amount)]
                    count = amount
                
                with open(file_path, 'a', encoding='utf-8') as f:
                    if key_type == "custom":
                        f.write(key + '\n')
                    else:
                        f.write(''.join(key) + '\n')
                embed = discord.Embed(title="SUCCESS!", description=f"Added {count} credit key in {key_type}", color=discord.Color.green())
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "remove":
            try:
                open(file_path, 'w').close()
                embed = discord.Embed(title="SUCCESS!", description=f"Removed credit key **{key_type}** all key", color=discord.Color.green())
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "show":
            try:
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                dm_channel = await interaction.user.create_dm()
                embed = discord.Embed(title=f"Here is {key_type} all key", color=discord.Color.blue())
                await dm_channel.send(embed=embed, file=discord.File(file_path))

                embed = discord.Embed(title="SUCCESS!", description=f"Key file **{key_type}** is sent to your dm", color=discord.Color.green())
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @creditkey.autocomplete('key_type')
    async def creditkey_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [
            app_commands.Choice(name=option, value=option)
            for option in self.creditkey_options
            if current.lower() in option.lower()
        ][:25]
        print(f"Creditkey autocomplete triggered with current: {current}, returning: {[c.name for c in choices]}")
        return choices

    @app_commands.command(name="redeem", description="Use redeem code to get credit")
    @app_commands.describe(code="Input your redeem code to here")
    async def redeem(self, interaction: discord.Interaction, code: str):
        code = code.strip()
        found = False
        points = 0
        target_file = None

        if os.path.exists('creditkey'):
            for txt_file in os.listdir('creditkey'):
                if txt_file.endswith('.txt'):
                    file_path = f'creditkey/{txt_file}'
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                        if code in lines:
                            found = True
                            target_file = file_path
                            if txt_file == "custom.txt":
                                # 自定义兑换码：提取 {随机码}.{金额} 中的金额
                                try:
                                    points = int(code.split('.')[-1])
                                except ValueError:
                                    embed = discord.Embed(title="WARNING!", description="Custom key invalid", color=discord.Color.red())
                                    await interaction.response.send_message(embed=embed, ephemeral=True)
                                    return
                            else:
                                # 标准兑换码：从文件名提取积分
                                try:
                                    points = int(txt_file[:-4])
                                except ValueError:
                                    embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred", color=discord.Color.red())
                                    await interaction.response.send_message(embed=embed, ephemeral=True)
                                    return
                            lines.remove(code)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write('\n'.join(lines) + '\n' if lines else '')
                            break

        if not found:
            embed = discord.Embed(title="WARNING!", description="Redeem key invalid", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user_id = str(interaction.user.id)
            users = {}
            if os.path.exists('users.json'):
                with open('users.json', 'r', encoding='utf-8') as f:
                    users = json.load(f)
            
            users[user_id] = users.get(user_id, 0) + points
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=4)
            
            embed = discord.Embed(title="SUCCESS!", description=f"You are geted **{points}** credit, now you has **{users[user_id]}** credit", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stock", description="View all product stock")
    async def stock(self, interaction: discord.Interaction):
        embed = discord.Embed(title="All product stock", color=discord.Color.blue())
        
        if os.path.exists('stock/file'):
            for folder in os.listdir('stock/file'):
                folder_path = f'stock/file/{folder}'
                if os.path.isdir(folder_path):
                    file_count = len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
                    embed.add_field(name=f"__{folder}__", value=f"**Stock** `{file_count}`", inline=False)
        
        if os.path.exists('stock/text'):
            for txt_file in os.listdir('stock/text'):
                if txt_file.endswith('.txt'):
                    file_path = f'stock/text/{txt_file}'
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        line_count = len([line for line in lines if line.strip()])
                    name = txt_file[:-4]
                    embed.add_field(name=f"__{name}__", value=f"**Stock** `{line_count}`", inline=False)
        
        if not embed.fields:
            embed.description = "No any product has stock ;("
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="balance", description="View your credit")
    @app_commands.describe(user_id="Input discord id")
    async def balance(self, interaction: discord.Interaction, user_id: str = None):
        if user_id:
            if not self.check_permission(interaction):
                embed = discord.Embed(title="WARNING!", description="You are not allowed to use this command", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            target_id = user_id
        else:
            target_id = str(interaction.user.id)

        try:
            users = {}
            if os.path.exists('users.json'):
                with open('users.json', 'r', encoding='utf-8') as f:
                    users = json.load(f)
            
            points = users.get(target_id, 0)
            embed = discord.Embed(title="SUCCESS!", description=f"User <@{target_id}> has **{points}** credit", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)




    @app_commands.command(name="purchase", description="Use this command to purchase product")
    @app_commands.describe(quantity="Purchase quantity")
    async def purchase(self, interaction, quantity: int):  # 移除 interaction 注解
        # 判断是否为私信
        is_dm = interaction.guild is None
        ephemeral = not is_dm  # 非私信时仅用户可见

        if quantity <= 0:
            embed = discord.Embed(title="WARNING!", description="Purchase quantity need positive integer", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            # 更新库存选项
            self.update_stock_options()

            # 读取 credit.json
            credit_data = {}
            credit_path = 'credit.json'
            if os.path.exists(credit_path):
                with open(credit_path, 'r', encoding='utf-8') as f:
                    try:
                        credit_data = json.load(f)
                    except json.JSONDecodeError:
                        credit_data = {}
            else:
                embed = discord.Embed(title="WARNING!", description="An unexpected error occurred: credit.json not found", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # 获取库存足够的商品
            available_products = []
            for name in self.stock_options:
                stock_count = 0
                is_file_type = False
                file_path = f'stock/file/{name}'
                text_path = f'stock/text/{name}.txt'

                try:
                    if os.path.exists(file_path) and os.path.isdir(file_path):
                        stock_count = len([f for f in os.listdir(file_path) if f.endswith('.txt') and os.path.isfile(os.path.join(file_path, f))])
                        is_file_type = True
                    elif os.path.exists(text_path):
                        with open(text_path, 'r', encoding='utf-8') as f:
                            stock_count = len([line for line in f if line.strip()])
                except Exception as e:
                    continue

                if stock_count >= quantity:
                    price = credit_data.get(name, 0)
                    available_products.append((name, price, is_file_type))

            if not available_products:
                embed = discord.Embed(title="WARNING!", description=f"No any product stock ≥ **{quantity}**", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                return

            # 创建下拉选单
            class ProductSelect(discord.ui.Select):
                def __init__(self):
                    options = [
                        discord.SelectOption(
                            label=name,
                            value=f"{name}:{is_file}",
                            description=f"Price: {price * quantity} ({price} credit/per)"
                        ) for name, price, is_file in available_products
                    ]
                    super().__init__(placeholder="Choose a product purchased from", options=options, min_values=1, max_values=1)

                async def callback(self, interaction):  # 移除 interaction 注解
                    selected_product, is_file_str = self.values[0].split(':')
                    is_file_type = is_file_str == 'True'
                    price = next(p for n, p, _ in available_products if n == selected_product)

                    # 读取用户积分
                    user_id = str(interaction.user.id)
                    users_data = {}
                    users_path = 'users.json'
                    if os.path.exists(users_path):
                        with open(users_path, 'r', encoding='utf-8') as f:
                            try:
                                users_data = json.load(f)
                            except json.JSONDecodeError:
                                users_data = {}
                    
                    user_points = users_data.get(user_id, 0)
                    total_cost = price * quantity

                    if user_points < total_cost:
                        embed = discord.Embed(title="WARNING!", description=f"Your credit `{user_points}` is not enough to purchase `{quantity}` __{selected_product}__ **(Need {total_cost} credit)**", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                        return

                    # 创建确认按钮
                    class ConfirmView(discord.ui.View):
                        def __init__(self):
                            super().__init__(timeout=60)

                        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
                        async def confirm(self, interaction, button: discord.ui.Button):
                            # 延迟交互响应，避免超时
                            await interaction.response.defer(ephemeral=ephemeral)

                            try:
                                # 扣除积分
                                users_data[user_id] = user_points - total_cost
                                with open(users_path, 'w', encoding='utf-8') as f:
                                    json.dump(users_data, f, indent=4, ensure_ascii=False)

                                # 生成订单号
                                random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                                order_id = f"{user_id}-{random_str}"
                                order_id_md5 = hashlib.md5(order_id.encode('utf-8')).hexdigest()

                                # 处理商品
                                if is_file_type:
                                    # File 类型：随机取 .txt 文件
                                    file_path = f'stock/file/{selected_product}'
                                    try:
                                        txt_files = [f for f in os.listdir(file_path) if f.endswith('.txt') and os.path.isfile(os.path.join(file_path, f))]
                                        if len(txt_files) < quantity:
                                            raise ValueError(f"{selected_product} only has {len(txt_files)} stock")
                                        selected_files = random.sample(txt_files, quantity)
                                        discord_files = [
                                            discord.File(os.path.join(file_path, f), filename=f) for f in selected_files
                                        ]

                                        # 发送私信
                                        embed = discord.Embed(title=f"Order ID {order_id_md5}", description=f"- **Product** `{selected_product}`\n- **Amount** `{quantity}`", color=discord.Color.blue())
                                        await interaction.user.send(embed=embed, files=discord_files)

                                        # 删除文件
                                        for f in selected_files:
                                            os.remove(os.path.join(file_path, f))
                                    except discord.Forbidden:
                                        # 回滚积分
                                        users_data[user_id] = user_points
                                        with open(users_path, 'w', encoding='utf-8') as f:
                                            json.dump(users_data, f, indent=4, ensure_ascii=False)
                                        embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred, **credit rollback**", color=discord.Color.red())
                                        await interaction.followup.send(
                                            embed=embed,
                                            ephemeral=ephemeral
                                        )
                                        return
                                    except Exception as e:
                                        # 回滚积分
                                        users_data[user_id] = user_points
                                        with open(users_path, 'w', encoding='utf-8') as f:
                                            json.dump(users_data, f, indent=4, ensure_ascii=False)
                                        embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred, **credit rollback**", color=discord.Color.red())
                                        await interaction.followup.send(
                                            embed=embed,
                                            ephemeral=ephemeral
                                        )
                                        return

                                else:
                                    # Text 类型：随机取非空行
                                    text_path = f'stock/text/{selected_product}.txt'
                                    try:
                                        with open(text_path, 'r', encoding='utf-8') as f:
                                            lines = [line.strip() for line in f if line.strip()]
                                        if len(lines) < quantity:
                                            raise ValueError(f"{selected_product} only has {len(lines)} stock")

                                        selected_lines = random.sample(lines, quantity)

                                        # 发送私信
                                        embed = discord.Embed(title=f"Order ID {order_id_md5}", description=f"- **Product** `{selected_product}`\n- **Amount** `{quantity}`\n||```\n" + "\n".join(selected_lines) + "\n```||", color=discord.Color.blue())
                                        await interaction.user.send(embed=embed)

                                        # 更新文本文件（移除已发送的行）
                                        remaining_lines = [line for line in lines if line not in selected_lines]
                                        with open(text_path, 'w', encoding='utf-8') as f:
                                            f.write('\n'.join(remaining_lines))
                                    except discord.Forbidden:
                                        # 回滚积分
                                        users_data[user_id] = user_points
                                        with open(users_path, 'w', encoding='utf-8') as f:
                                            json.dump(users_data, f, indent=4, ensure_ascii=False)
                                        embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred, **credit rollback**", color=discord.Color.red())
                                        await interaction.followup.send(
                                            embed=embed,
                                            ephemeral=ephemeral
                                        )
                                        return
                                    except Exception as e:
                                        # 回滚积分
                                        users_data[user_id] = user_points
                                        with open(users_path, 'w', encoding='utf-8') as f:
                                            json.dump(users_data, f, indent=4, ensure_ascii=False)
                                        embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred, **credit rollback**", color=discord.Color.red())
                                        await interaction.followup.send(
                                            embed=embed,
                                            ephemeral=ephemeral
                                        )
                                        return

                                # 创建订单文件
                                os.makedirs('order', exist_ok=True)
                                order_file = f'order/{order_id_md5}.txt'
                                with open(order_file, 'w', encoding='utf-8') as f:
                                    f.write(f"Order ID: {order_id_md5}\n")
                                    f.write(f"Customer: {user_id}\n")
                                    f.write(f"Time (unix time): {int(time.time())}\n")
                                    f.write(f"Product: {selected_product}, Amount: {quantity}\n")

                                # 更新交互
                                self.confirm.disabled = True
                                self.cancel.disabled = True
                                embed = discord.Embed(title="SUCCESS!", description=f"Order ID `{order_id}`", color=discord.Color.green())
                                await interaction.edit_original_response(
                                    embed=embed,
                                    view=self
                                )

                            except Exception as e:
                                embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
                                await interaction.followup.send(
                                    embed=embed,
                                    ephemeral=ephemeral
                                )

                        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
                        async def cancel(self, interaction, button: discord.ui.Button):  # 移除 interaction 注解
                            self.confirm.disabled = True
                            self.cancel.disabled = True
                            embed = discord.Embed(title="SUCCESS!", description=f"Canceled purchase", color=discord.Color.green())
                            await interaction.response.edit_message(embed=embed, view=self)

                        async def on_timeout(self):
                            self.confirm.disabled = True
                            self.cancel.disabled = True
                            await interaction.edit_original_response(content="Purchase timeout", view=self)

                    view = ConfirmView()
                    embed = discord.Embed(title="", description="You selected {quantity} {selected_product} total credit {total_cost} , Confirm your purchase?", color=discord.Color.green())
                    await interaction.response.send_message(
                        embed=embed,
                        view=view,
                        ephemeral=ephemeral
                    )

            view = discord.ui.View()
            view.add_item(ProductSelect())
            await interaction.response.send_message("Please select a product", view=view, ephemeral=ephemeral)

        except Exception as e:
            embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)



    @app_commands.command(name="order", description="Show order info")
    @app_commands.describe(order_id="Input your order id (md5)")
    async def order(self, interaction: discord.Interaction, order_id: str):
        try:
            order_id_md5 = hashlib.md5(order_id.encode('utf-8')).hexdigest()
            order_file = f'order/{order_id_md5}.txt'

            if not os.path.exists(order_file):
                embed = discord.Embed(title="WARNING!", description=f"Order ID `{order_id}` is does not exist", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            with open(order_file, 'r', encoding='utf-8') as f:
                file_content = f.read()

            file = discord.File(order_file, filename=f"{order_id}.txt")
            embed = discord.Embed(title="SUCCESS!", description=f"Order ID `{order_id}` details", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, file=file, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    commands_cog = Commands(bot)
    product_group = commands_cog.Product(name="product")
    bot.tree.add_command(product_group)
    await bot.add_cog(commands_cog)