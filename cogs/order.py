import discord
from discord import app_commands
from discord.ext import commands
import os
import json

def load_permissions():
    try:
        with open('configs/permissions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"users": [], "roles": []}

def has_special_permission(user_id, role_ids):
    permissions = load_permissions()
    user_id_str = str(user_id).strip()
    role_ids_str = [str(role_id).strip() for role_id in role_ids]
    user_has_permission = user_id_str in [str(user).strip() for user in permissions['users']]
    role_has_permission = any(str(role_id).strip() in [str(role).strip() for role in permissions['roles']] for role_id in role_ids_str)
    return user_has_permission or role_has_permission

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

            with open(order_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) < 3:
                    await interaction.response.send_message("Invalid order file format!", ephemeral=True)
                    return

                order_by_line = lines[2].strip()
                if not order_by_line.startswith("Order By: "):
                    await interaction.response.send_message("Invalid order file format!", ephemeral=True)
                    return

                order_user_id = order_by_line[len("Order By: "):].strip()
                requester_id = str(interaction.user.id)

                is_order_owner = order_user_id == requester_id

                has_permission = has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles])

                if not is_order_owner and not has_permission:
                    await interaction.response.send_message("You do not have permission to view this order!", ephemeral=True)
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