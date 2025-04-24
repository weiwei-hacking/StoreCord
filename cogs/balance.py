import discord
from discord import app_commands
from discord.ext import commands
import json
import random
from datetime import datetime

def load_permissions():
    try:
        with open('configs/permissions.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"load permissions.json fail: {e}")
        return {"users": [], "roles": []}

def load_balances():
    try:
        with open('configs/balance.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"load balance.json fail: {e}")
        return {}

def save_balances(balances):
    try:
        with open('configs/balance.json', 'w') as f:
            json.dump(balances, f, indent=4)
    except Exception as e:
        print(f"Error saving balance.json: {e}")

def has_special_permission(user_id, role_ids):
    permissions = load_permissions()
    user_id_str = str(user_id).strip()
    role_ids_str = [str(role_id).strip() for role_id in role_ids]
    user_has_permission = user_id_str in [str(user).strip() for user in permissions['users']]
    role_has_permission = any(str(role_id).strip() in [str(role).strip() for role in permissions['roles']] for role_id in role_ids_str)
    return user_has_permission or role_has_permission

class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Show a user's credits")
    @app_commands.describe(member="The user to query (defaults to yourself)")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user

        if member != interaction.user:
            if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
                await interaction.response.send_message("You do not have permission to query other users' credits!", ephemeral=True)
                return

        balances = load_balances()
        user_id_str = str(member.id)
        credits = balances.get(user_id_str, 0)

        random_color = discord.Color(random.randint(0, 0xFFFFFF))
        embed = discord.Embed(
            title=f"Balances of {member.display_name}",
            color=random_color,
            timestamp=datetime.now()
        )
        embed.add_field(name=f"{str(credits)} credits", value="", inline=True)
        embed.set_footer(text=f"Queried by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    balance_group = app_commands.Group(name="credits", description="Manage user credits")

    @balance_group.command(name="modify", description="Modify a user's credits")
    @app_commands.describe(
        member="The user to modify credits for",
        action="Add or remove credits",
        amount="The amount of credits to add or remove"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove")
    ])
    async def balance_modify(self, interaction: discord.Interaction, member: discord.Member, action: str, amount: int):
        if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
            return

        if amount < 0:
            await interaction.response.send_message("Amount must be a positive number!", ephemeral=True)
            return

        balances = load_balances()
        user_id_str = str(member.id)
        current_credits = balances.get(user_id_str, 0)

        if action == "add":
            balances[user_id_str] = current_credits + amount
            save_balances(balances)
            await interaction.response.send_message(f"Added {amount} credits to {member.mention}. New balance: {balances[user_id_str]}")
        else:
            if amount > current_credits:
                view = ConfirmView(interaction, member, current_credits)
                await interaction.response.send_message(
                    f"{member.mention} only has {current_credits} credits, but you want to remove {amount}. "
                    f"Do you want to remove all {current_credits} credits instead?",
                    view=view,
                    ephemeral=True
                )
            else:
                balances[user_id_str] = current_credits - amount
                save_balances(balances)
                await interaction.response.send_message(f"Removed {amount} credits from {member.mention}. New balance: {balances[user_id_str]}")

class ConfirmView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, member: discord.Member, current_credits: int):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.member = member
        self.current_credits = current_credits

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        balances = load_balances()
        user_id_str = str(self.member.id)
        balances[user_id_str] = 0
        save_balances(balances)
        await interaction.response.send_message(f"All {self.current_credits} credits have been removed from {self.member.mention}. New balance: 0")
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Action cancelled.", ephemeral=True)
        self.stop()

async def setup(bot):
    await bot.add_cog(Balance(bot))