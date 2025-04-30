import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import aiofiles

def load_permissions():
    try:
        with open('configs/permissions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"users": [], "roles": []}

def load_prices():
    try:
        with open('configs/price.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        return {}

def save_prices(prices):
    try:
        with open('configs/price.json', 'w', encoding='utf-8') as f:
            json.dump(prices, f, indent=4, ensure_ascii=False)
    except Exception as e:
        pass

def has_special_permission(user_id, role_ids):
    permissions = load_permissions()
    user_id_str = str(user_id).strip()
    role_ids_str = [str(role_id).strip() for role_id in role_ids]
    user_has_permission = user_id_str in [str(user).strip() for user in permissions['users']]
    role_has_permission = any(str(role_id).strip() in [str(role).strip() for role in permissions['roles']] for role_id in role_ids_str)
    return user_has_permission or role_has_permission

class Product(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def file_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        stock_dir = 'stock'
        if not os.path.exists(stock_dir):
            return []
        txt_files = [f[:-4] for f in os.listdir(stock_dir) if f.endswith('.txt')]
        return [
            app_commands.Choice(name=file, value=file)
            for file in txt_files
            if current.lower() in file.lower()
        ][:25]

    product_group = app_commands.Group(name="product", description="Manage products and advanced modify stock")

    @product_group.command(name="create", description="Create a new product")
    @app_commands.describe(
        name="The name of the product",
        price="The price of the product",
        limit="The purchase limit per transaction (optional)"
    )
    async def create(self, interaction: discord.Interaction, name: str, price: int, limit: int = None):
        if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
            return

        if not name.isalnum():
            await interaction.response.send_message("Product name can only contain letters and numbers!", ephemeral=True)
            return

        if price < 0:
            await interaction.response.send_message("Price cannot be negative!", ephemeral=True)
            return

        if limit is not None and limit <= 0:
            await interaction.response.send_message("Limit must be a positive number!", ephemeral=True)
            return

        stock_dir = 'stock'
        if not os.path.exists(stock_dir):
            os.makedirs(stock_dir)
        target_file = os.path.join(stock_dir, f"{name}.txt")

        if os.path.exists(target_file):
            await interaction.response.send_message(f"Product '{name}' already exists!", ephemeral=True)
            return

        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                pass
        except Exception as e:
            await interaction.response.send_message(f"Failed to create file: {e}", ephemeral=True)
            return

        prices = load_prices()
        prices[f"{name}.txt"] = {"price": price, "limit": limit}
        save_prices(prices)

        await interaction.response.send_message(f"Successfully created product '{name}' with price {price}" + (f" and limit {limit}" if limit is not None else "") + "!", ephemeral=True)

    @product_group.command(name="remove", description="Remove a product")
    @app_commands.describe(file="The product to remove")
    @app_commands.autocomplete(file=file_autocomplete)
    async def remove(self, interaction: discord.Interaction, file: str):
        if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
            return

        stock_dir = 'stock'
        if not os.path.exists(stock_dir):
            await interaction.response.send_message("Stock directory does not exist!", ephemeral=True)
            return

        txt_files = [f[:-4] for f in os.listdir(stock_dir) if f.endswith('.txt')]
        if file not in txt_files:
            await interaction.response.send_message(f"Product '{file}' does not exist! Available products: {', '.join(txt_files)}", ephemeral=True)
            return

        class ConfirmView(discord.ui.View):
            def __init__(self, timeout=60):
                super().__init__(timeout=timeout)
                self.value = None

            @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                self.stop()

            @discord.ui.button(label="No", style=discord.ButtonStyle.red)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                self.stop()

        view = ConfirmView()
        await interaction.response.send_message(f"Are you sure you want to delete product '{file}'?", view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            await interaction.response.send_message("Operation timed out, product not deleted.", ephemeral=True)
            return
        if not view.value:
            await interaction.response.send_message("Deletion canceled.", ephemeral=True)
            return

        target_file = os.path.join(stock_dir, f"{file}.txt")
        try:
            os.remove(target_file)
        except Exception as e:
            await interaction.response.send_message(f"Failed to delete file: {e}", ephemeral=True)
            return

        prices = load_prices()
        if f"{file}.txt" in prices:
            del prices[f"{file}.txt"]
            save_prices(prices)

        await interaction.response.send_message(f"Successfully deleted product '{file}'!", ephemeral=True)

    @product_group.command(name="stock", description="Manage product stock")
    @app_commands.describe(
        action="The action to perform",
        file="The product to manage",
        attachment="The txt file to upload (only for update)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="remove", value="remove"),
        app_commands.Choice(name="download", value="download"),
        app_commands.Choice(name="update", value="update")
    ])
    @app_commands.autocomplete(file=file_autocomplete)
    async def stock(self, interaction: discord.Interaction, action: str, file: str, attachment: discord.Attachment = None):
        if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
            return

        stock_dir = 'stock'
        if not os.path.exists(stock_dir):
            await interaction.response.send_message("Stock directory does not exist!", ephemeral=True)
            return

        txt_files = [f[:-4] for f in os.listdir(stock_dir) if f.endswith('.txt')]
        if file not in txt_files:
            await interaction.response.send_message(f"Product '{file}' does not exist! Available products: {', '.join(txt_files)}", ephemeral=True)
            return

        target_file = os.path.join(stock_dir, f"{file}.txt")

        if action == "remove":
            try:
                with open(target_file, 'w', encoding='utf-8') as f:
                    pass
                await interaction.response.send_message(f"Successfully cleared all contents of product '{file}'!", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Failed to clear file contents: {e}", ephemeral=True)

        elif action == "download":
            try:
                if not os.path.exists(target_file):
                    await interaction.response.send_message(f"File '{file}.txt' does not exist!", ephemeral=True)
                    return

                file_size = os.path.getsize(target_file)
                if file_size == 0:
                    await interaction.response.send_message(f"File '{file}.txt' is empty and cannot be downloaded!", ephemeral=True)
                    return

                discord_file = discord.File(target_file, filename=f"{file}.txt")
                try:
                    await interaction.user.send(file=discord_file)
                    await interaction.response.send_message("File has been sent to your DMs!", ephemeral=True)
                except discord.Forbidden:
                    discord_file = discord.File(target_file, filename=f"{file}.txt")
                    await interaction.response.send_message(file=discord_file, ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Failed to download file: {e}", ephemeral=True)

        elif action == "update":
            if not attachment:
                await interaction.response.send_message("Please provide a txt file to update!", ephemeral=True)
                return

            if not attachment.filename.endswith('.txt'):
                await interaction.response.send_message("Please upload a txt file!", ephemeral=True)
                return

            try:
                content = await attachment.read()
                async with aiofiles.open(target_file, 'wb') as f:
                    await f.write(content)
                await interaction.response.send_message(f"Successfully updated the contents of product '{file}'!", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Failed to update file: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Product(bot))