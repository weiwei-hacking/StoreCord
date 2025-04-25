import discord
from discord import app_commands
from discord.ext import commands
import json
import random
from datetime import datetime

def load_permissions():
    try:
        with open('configs/permissions.json', 'r') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Error loading permissions.json: {e}")
        return {"users": [], "roles": []}

def has_special_permission(user_id, role_ids):
    permissions = load_permissions()
    user_id_str = str(user_id).strip()
    role_ids_str = [str(role_id).strip() for role_id in role_ids]

    user_has_permission = user_id_str in [str(user).strip() for user in permissions['users']]

    role_has_permission = any(str(role_id).strip() in [str(role).strip() for role in permissions['roles']] for role_id in role_ids_str)

    final_result = user_has_permission or role_has_permission
    return final_result

class UserPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="user", description="Show information about a specified user")
    @app_commands.describe(member="The user to query (defaults to yourself)")
    async def user(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user

        is_special = has_special_permission(member.id, [role.id for role in member.roles])

        random_color = discord.Color(random.randint(0, 0xFFFFFF))

        embed = discord.Embed(
            title=f"Information about {member.display_name}",
            color=random_color,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(
            name="Account Creation Time",
            value=f"<t:{int(member.created_at.timestamp())}:f>",
            inline=True
        )
        embed.add_field(
            name="Server Join Time",
            value=f"<t:{int(member.joined_at.timestamp())}:f>",
            inline=True
        )
        embed.set_footer(text=f"Queried by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UserPanel(bot))
