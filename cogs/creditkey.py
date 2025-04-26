import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
import json
import os
import random
import string

def load_permissions():
    try:
        with open('configs/permissions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading permissions.json: {e}")
        return {"users": [], "roles": []}

def load_configs():
    try:
        with open('configs/normal.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading normal.json: {e}")
        return {}

def has_special_permission(user_id, role_ids):
    permissions = load_permissions()
    user_id_str = str(user_id).strip()
    role_ids_str = [str(role_id).strip() for role_id in role_ids]
    user_has_permission = user_id_str in [str(user).strip() for user in permissions['users']]
    role_has_permission = any(str(role_id).strip() in [str(role).strip() for role in permissions['roles']] for role_id in role_ids_str)
    return user_has_permission or role_has_permission

class creditkey(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.creditkey_options = []
        if os.path.exists('creditkey'):
            self.creditkey_options.extend([f[:-4] for f in os.listdir('creditkey') if f.endswith('.txt')])
        print(f"Loaded creditkey options: {self.creditkey_options}")

    def generate_key(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

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
        if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
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
                    key = f"{self.generate_key()}.{amount}"
                    count = 1
                else:
                    key = [self.generate_key() for _ in range(amount)]
                    count = amount

                with open(file_path, 'a', encoding='utf-8') as f:
                    if os.path.getsize(file_path) > 0:
                        f.write('\n')
                    if key_type == "custom":
                        f.write(key + '\n')
                    else:
                        f.write('\n'.join(key) + '\n')
                if key_type == "custom":
                    embed = discord.Embed(title="SUCCESS!", description=f"Added {count} credit key in {key_type}\n\n||```{key}```||", color=discord.Color.green())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    embed = discord.Embed(title="SUCCESS!", description=f"Added {count} credit key in {key_type}\n\n||```"+'\n'.join(key) + '\n```||', color=discord.Color.green())
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
                    embed = discord.Embed(title="WARNING!", description="No keys found in this key type!", color=discord.Color.red())
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
        key_type = None

        if os.path.exists('creditkey'):
            for txt_file in os.listdir('creditkey'):
                if txt_file.endswith('.txt'):
                    file_path = f'creditkey/{txt_file}'
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                        if code in lines:
                            found = True
                            target_file = file_path
                            key_type = txt_file[:-4]  # Remove .txt extension
                            if txt_file == "custom.txt":
                                try:
                                    points = int(code.split('.')[-1])
                                except ValueError:
                                    embed = discord.Embed(title="WARNING!", description="Custom key invalid", color=discord.Color.red())
                                    await interaction.response.send_message(embed=embed, ephemeral=True)
                                    return
                            else:
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
            balance_file = 'configs/balance.json'
            configs_dir = 'configs'
            
            if not os.path.exists(configs_dir):
                os.makedirs(configs_dir)
            
            if os.path.exists(balance_file):
                with open(balance_file, 'r', encoding='utf-8') as f:
                    users = json.load(f)
            else:
                with open(balance_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
            
            users[user_id] = users.get(user_id, 0) + points
            with open(balance_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=4)
            
            # Send success message to the user
            embed = discord.Embed(title="SUCCESS!", description=f"You are geted **{points}** credit, now you has **{users[user_id]}** credit", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Load channel IDs from configs/normal.json
            configs = load_configs()
            public_logs_id = configs.get('public_logs')
            private_logs_id = configs.get('private_logs')

            # Get current Unix timestamp
            current_time = int(discord.utils.utcnow().timestamp())

            # Send to public_logs channel
            if public_logs_id:
                public_channel = self.bot.get_channel(int(public_logs_id))
                if public_channel:
                    embed = discord.Embed(
                        title=(f"**{key_type}** credit key redeemed"),
                        description=f"Someone redeemed the **{key_type}** credit key {code} at <t:{current_time}:R>.",
                        color=discord.Color.gold(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_footer(text="Credit Redeemed")
                    await public_channel.send(embed=embed)
                else:
                    print(f"Could not find public_logs channel ID: {public_logs_id}")

            # Send to private_logs channel
            if private_logs_id:
                private_channel = self.bot.get_channel(int(private_logs_id))
                if private_channel:
                    try:
                        embed = discord.Embed(
                            title=(f"**{key_type}** credit key redeemed"),
                            description=(
                                f"{interaction.user.mention} redeemed the **{key_type}** credit key {code} at <t:{current_time}:T>\n"
                                f"New balance: {users[user_id]}"
                            ),
                            color=discord.Color.blue(),
                            timestamp=discord.utils.utcnow()
                        )
                        embed.set_footer(text="Credit Redeemed")
                        await private_channel.send(embed=embed)
                        print(f"Successfully sent redeem log to private_logs channel: {private_logs_id}")
                    except Exception as e:
                        print(f"Failed to send to private_logs channel {private_logs_id}: {e}")
                else:
                    print(f"Could not find or access private_logs channel ID: {private_logs_id}")
            else:
                print("private_logs channel ID not provided, skipping private log.")

        except Exception as e:
            embed = discord.Embed(title="WARNING!", description=f"An unexpected error occurred\n```{str(e)}```", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    cog_instance = creditkey(bot)
    await bot.add_cog(cog_instance)