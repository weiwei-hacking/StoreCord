import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import pandas as pd
import tempfile
from datetime import datetime
import pytz

# Load permission settings
def load_permissions():
    try:
        with open('configs/permissions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading permissions.json: {e}")
        return {"users": [], "roles": []}

# Check special permission
def has_special_permission(user_id, role_ids):
    permissions = load_permissions()
    user_id_str = str(user_id).strip()
    role_ids_str = [str(role_id).strip() for role_id in role_ids]
    user_has_permission = user_id_str in [str(user).strip() for user in permissions['users']]
    role_has_permission = any(str(role_id).strip() in [str(role).strip() for role in permissions['roles']] for role_id in role_ids_str)
    return user_has_permission or role_has_permission

class Excel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="excel", description="Convert all txt files in the order folder to an Excel file")
    async def excel(self, interaction: discord.Interaction):
        # Check permission
        if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
            return

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

        # Extract data
        data = []
        skipped_files = []
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

                # Extract values after the colon
                order_id = lines[0].split(':', 1)[1].strip() if ':' in lines[0] else lines[0]
                order_time_line = lines[1].split(':', 1)[1].strip() if ':' in lines[1] else lines[1]
                order_by = lines[2].split(':', 1)[1].strip() if ':' in lines[2] else lines[2]
                product_name = lines[4].split(':', 1)[1].strip() if ':' in lines[4] else lines[4]
                amount = lines[5].split(':', 1)[1].strip() if ':' in lines[5] else lines[5]
                price = lines[6].split(':', 1)[1].strip() if ':' in lines[6] else lines[6]

                # Convert Order Time to Unix timestamp
                order_time_unix = int(order_time_line)

                # Convert Unix timestamp to Taiwan time (UTC+8)
                tz = pytz.timezone('Asia/Taipei')
                order_time = datetime.fromtimestamp(order_time_unix, tz)
                order_time_str = order_time.strftime('%Y/%m/%d - %H:%M:%S')

                # Store data
                data.append({
                    'Order ID': order_id,
                    'Order Time': order_time_str,
                    'Order Time Unix': order_time_unix,  # For sorting
                    'Order By': order_by,
                    'Product name': product_name,
                    'Amount': amount,
                    'Price': price
                })
            except Exception as e:
                print(f"Error processing file {txt_file}: {e}")
                skipped_files.append(txt_file)
                continue

        # Check if there is any data
        if not data:
            message = "No valid order data to convert!"
            if skipped_files:
                message += f"\nSkipped files due to errors: {', '.join(skipped_files)}"
            await interaction.response.send_message(message, ephemeral=True)
            return

        # Sort by Order Time (newest to oldest)
        data.sort(key=lambda x: x['Order Time Unix'], reverse=True)

        # Remove the temporary column used for sorting
        for entry in data:
            entry.pop('Order Time Unix')

        # Convert to DataFrame
        df = pd.DataFrame(data, columns=['Order ID', 'Order Time', 'Order By', 'Product name', 'Amount', 'Price'])

        # Generate Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            excel_path = tmp.name
            df.to_excel(excel_path, index=False)

        # Generate file name
        current_time = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y%m%d_%H%M%S')
        excel_filename = f"orders_{current_time}.xlsx"

        # Try to send via DM
        try:
            dm_channel = await interaction.user.create_dm()
            embed = discord.Embed(title="Order Data", description="Here is your requested order Excel file", color=discord.Color.blue())
            await dm_channel.send(embed=embed, file=discord.File(excel_path, filename=excel_filename))
            await interaction.response.send_message("The Excel file has been sent to you via DM!", ephemeral=True)
        except Exception as e:
            print(f"Unable to send DM to user {interaction.user.id}: {e}")
            embed = discord.Embed(title="Order Data", description="Unable to send via DM, please check in this channel", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed, file=discord.File(excel_path, filename=excel_filename), ephemeral=True)

        # Clean up temporary file
        os.remove(excel_path)

async def setup(bot):
    await bot.add_cog(Excel(bot))