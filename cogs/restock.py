import discord
from discord import app_commands
from discord.ext import commands
import json
import random
from datetime import datetime
import os

def load_permissions():
    try:
        with open('configs/permissions.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading permissions.json: {e}")
        return {"users": [], "roles": []}

def load_configs():
    try:
        with open('configs/normal.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading normal.json: {e}")
        return {}

def load_prices():
    try:
        with open('configs/price.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading price.json: {e}")
        return {}

def has_special_permission(user_id, role_ids):
    permissions = load_permissions()
    user_id_str = str(user_id).strip()
    role_ids_str = [str(role_id).strip() for role_id in role_ids]
    user_has_permission = user_id_str in [str(user).strip() for user in permissions['users']]
    role_has_permission = any(str(role_id).strip() in [str(role).strip() for role in permissions['roles']] for role_id in role_ids_str)
    return user_has_permission or role_has_permission

class Restock(commands.Cog):
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

    @app_commands.command(name="restock", description="Restock a txt file with uploaded content")
    @app_commands.describe(
        file="The txt file to restock",
        attachment="The txt file to upload"
    )
    @app_commands.autocomplete(file=file_autocomplete)
    async def restock(self, interaction: discord.Interaction, file: str, attachment: discord.Attachment):
        if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
            return

        if not attachment.filename.endswith('.txt'):
            await interaction.response.send_message("Please upload a .txt file!", ephemeral=True)
            return

        stock_dir = 'stock'
        if not os.path.exists(stock_dir):
            await interaction.response.send_message("Stock directory not found!", ephemeral=True)
            return

        txt_files = [f[:-4] for f in os.listdir(stock_dir) if f.endswith('.txt')]
        if file not in txt_files:
            await interaction.response.send_message(f"File '{file}' not found in stock directory! Available files: {', '.join(txt_files)}", ephemeral=True)
            return

        try:
            content = await attachment.read()
            lines = content.decode('utf-8').splitlines()
            non_empty_lines = [line.strip() for line in lines if line.strip()]
        except Exception as e:
            await interaction.response.send_message(f"Failed to read the uploaded file: {e}", ephemeral=True)
            return

        target_file = os.path.join(stock_dir, f"{file}.txt")
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        except Exception as e:
            await interaction.response.send_message(f"Failed to read the target file: {e}", ephemeral=True)
            return

        needs_newline = False
        if existing_lines:
            try:
                with open(target_file, 'rb') as f:
                    f.seek(-1, os.SEEK_END)
                    last_char = f.read(1).decode('utf-8')
                    needs_newline = last_char != '\n'
            except Exception as e:
                await interaction.response.send_message(f"Failed to check the target file's last character: {e}", ephemeral=True)
                return

        try:
            with open(target_file, 'a', encoding='utf-8') as f:
                if needs_newline:
                    f.write('\n')
                f.write('\n'.join(non_empty_lines))
                if non_empty_lines:
                    f.write('\n')
        except Exception as e:
            await interaction.response.send_message(f"Failed to write to the target file: {e}", ephemeral=True)
            return

        configs = load_configs()
        restock_channel_id = configs.get('restock_channel')
        restock_notify = configs.get('restock_notify', '')

        if restock_channel_id:
            channel = self.bot.get_channel(int(restock_channel_id))
            if channel:
                mention = ''
                if restock_notify == '@everyone':
                    mention = '@everyone'
                elif restock_notify == '@here':
                    mention = '@here'
                elif restock_notify:
                    mention = f"<@&{restock_notify}>"

                restock_count = len(non_empty_lines)
                random_color = discord.Color(random.randint(0, 0xFFFFFF))
                embed = discord.Embed(
                    title="Restock Notification",
                    description=f"Product `{file}` has been restocked with **{restock_count} units!**",
                    color=random_color,
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Stock Updated")

                await channel.send(content=mention, embed=embed)
            else:
                print(f"Could not find the specified restock channel ID: {restock_channel_id}")

        await interaction.response.send_message(f"Successfully restocked '{file}'!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Restock(bot))