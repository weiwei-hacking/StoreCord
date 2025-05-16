import discord
from discord import app_commands
from discord.ext import commands
import json
import time
import asyncio
from datetime import datetime
import random
import logging

# 設置日誌以便調試
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_permissions():
    try:
        with open('configs/permissions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"users": [], "roles": []}

def has_special_permission(user_id, role_ids):
    permissions = load_permissions()
    user_id_str = str(user_id).strip()
    role_ids_str = [str(role_id).strip() for role_id in role_ids]
    user_has_permission = user_id_str in [str(user).strip() for user in permissions['users']]
    role_has_permission = any(str(role_id).strip() in [str(role).strip() for role in permissions['roles']] for role_id in role_ids_str)
    return user_has_permission or role_has_permission

def load_giveaways():
    try:
        with open('configs/autogiveaway.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def save_giveaways(data):
    with open('configs/autogiveaway.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def load_balances():
    try:
        with open('configs/balance.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def save_balances(data):
    with open('configs/balance.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

class AutoGiveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaways = load_giveaways()
        self.bot.loop.create_task(self.check_giveaways())
        self.bot.loop.create_task(self.update_participant_count())

    async def update_giveaway_message(self, channel, giveaway_id, mention, winners, prize, entries_count):
        embed = discord.Embed(
            title="Credit Giveaway!",
            description=f"Good Luck for `{winners} winners` with **{prize} credit**!\nEntries: **{entries_count}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        view = discord.ui.View(timeout=None)
        view.add_item(self.GiveawayButton(giveaway_id))
        message = await channel.send(content=mention if mention else "", embed=embed, view=view)
        return message

    async def edit_giveaway_message(self, channel, message_id, mention, winners, prize, entries_count, giveaway_id):
        embed = discord.Embed(
            title="Credit Giveaway!",
            description=f"Good Luck for `{winners} winners` with **{prize} credit**!\nEntries: **{entries_count}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        view = discord.ui.View(timeout=None)
        view.add_item(self.GiveawayButton(giveaway_id))
        try:
            message = await channel.fetch_message(message_id)
            # 檢查權限
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.manage_messages:
                logger.warning("Bot lacks MANAGE_MESSAGES permission to edit giveaway message.")
                # 如果無法編輯，發送新訊息並更新 message_id
                new_message = await channel.send(content=mention if mention else "", embed=embed, view=view)
                return new_message.id
            await message.edit(embed=embed, view=view)
            return message.id
        except discord.HTTPException as e:
            logger.error(f"Failed to edit message {message_id}: {e}")
            # 如果編輯失敗，發送新訊息並更新 message_id
            new_message = await channel.send(content=mention if mention else "", embed=embed, view=view)
            return new_message.id

    async def send_giveaway_message(self, channel, giveaway_id, mention, winners, prize):
        giveaways = load_giveaways()
        giveaway = giveaways.get(str(giveaway_id))
        entry_count = len(giveaway.get('entries', [])) if giveaway else 0
        return await self.update_giveaway_message(channel, giveaway_id, mention, winners, prize, entry_count)

    async def update_participant_count(self):
        while True:
            current_time = int(time.time())
            giveaways = load_giveaways()
            for giveaway_id, giveaway in giveaways.items():
                if giveaway.get('start_time', 0) > 0 and current_time >= giveaway['start_time']:
                    if (current_time - giveaway['start_time']) % 3 == 0:  # 每 3 秒檢查一次
                        channel = self.bot.get_channel(giveaway['channel'])
                        if channel:
                            entries_count = len(giveaway.get('entries', []))
                            last_count = giveaway.get('last_count', -1)
                            if entries_count != last_count:  # 人數增加或減少時觸發
                                new_message_id = await self.edit_giveaway_message(
                                    channel, giveaway['message'], giveaway['mention'],
                                    giveaway['winners'], giveaway['prize'], entries_count, giveaway_id
                                )
                                if new_message_id != giveaway['message']:
                                    giveaway['message'] = new_message_id
                                giveaway['last_count'] = entries_count
                                giveaways[giveaway_id] = giveaway
                                save_giveaways(giveaways)
            await asyncio.sleep(1)  # 每秒檢查一次，配合 % 3 實現每 3 秒更新

    async def check_giveaways(self):
        while True:
            current_time = int(time.time())
            giveaways = load_giveaways()
            for giveaway_id, giveaway in list(giveaways.items()):
                # 檢查是否需要發送第一次抽獎（nexttime 模式）
                if giveaway.get('pending', False) and current_time >= giveaway['first_time']:
                    channel = self.bot.get_channel(giveaway['channel'])
                    if not channel:
                        del giveaways[giveaway_id]
                        save_giveaways(giveaways)
                        continue

                    # 發送第一次抽獎，參加人數立即歸 0
                    message = await self.update_giveaway_message(
                        channel, giveaway_id, giveaway['mention'], giveaway['winners'], giveaway['prize'], 0
                    )
                    giveaway['message'] = message.id
                    giveaway['time'] = current_time + (giveaway['first_time'] - giveaway['start_time'])
                    giveaway['pending'] = False
                    giveaway['last_count'] = 0  # 立即重置參加人數
                    giveaway['start_time'] = current_time  # 重新計算 3 秒計時
                    giveaways[giveaway_id] = giveaway
                    save_giveaways(giveaways)
                    continue

                # 檢查是否到達抽獎結束時間
                if current_time >= giveaway['time']:
                    channel = self.bot.get_channel(giveaway['channel'])
                    if not channel:
                        del giveaways[giveaway_id]
                        save_giveaways(giveaways)
                        continue

                    try:
                        old_message = await channel.fetch_message(giveaway['message'])
                        await old_message.delete()
                    except discord.HTTPException:
                        pass  # 忽略刪除失敗的情況

                    entries = giveaway.get('entries', [])
                    winners_count = min(giveaway['winners'], len(entries))
                    if winners_count == 0:
                        await channel.send("Giveaway Ended `No participants in the giveaway`")
                    else:
                        winners = random.sample(entries, winners_count)
                        prize = giveaway['prize']

                        # 更新中獎者積分
                        balances = load_balances()
                        for winner_id in winners:
                            winner_id_str = str(winner_id)
                            balances[winner_id_str] = balances.get(winner_id_str, 0) + prize
                        save_balances(balances)

                        # 發送中獎訊息
                        winner_mentions = ', '.join(f"<@{winner_id}>" for winner_id in winners)
                        await channel.send(f"Congratulations {winner_mentions}! You won the **{prize} credit**!")

                    # 發送新的抽獎，參加人數立即歸 0
                    new_message = await self.update_giveaway_message(
                        channel, giveaway_id, giveaway['mention'], giveaway['winners'], giveaway['prize'], 0
                    )

                    # 更新抽獎資訊
                    giveaway['message'] = new_message.id
                    giveaway['time'] = current_time + (giveaway['time'] - giveaway['start_time'])
                    giveaway['entries'] = []
                    giveaway['last_count'] = 0  # 立即重置參加人數
                    giveaway['start_time'] = current_time  # 重新計算 3 秒計時
                    giveaways[giveaway_id] = giveaway
                    save_giveaways(giveaways)

            await asyncio.sleep(1)  # 每秒檢查一次

    class LeaveGiveawayButton(discord.ui.Button):
        def __init__(self, giveaway_id, user_id):
            super().__init__(label="Leave giveaway", style=discord.ButtonStyle.danger)
            self.giveaway_id = giveaway_id
            self.user_id = user_id

        async def callback(self, interaction: discord.Interaction):
            giveaways = load_giveaways()
            giveaway = giveaways.get(str(self.giveaway_id))
            if not giveaway:
                await interaction.response.send_message("This giveaway has ended or does not exist.", ephemeral=True)
                return

            entries = giveaway.get('entries', [])
            if self.user_id not in entries:
                await interaction.response.send_message("You are not in this giveaway!", ephemeral=True)
                return

            entries.remove(self.user_id)
            giveaway['entries'] = entries
            giveaways[str(self.giveaway_id)] = giveaway
            save_giveaways(giveaways)

            await interaction.response.send_message("You have left the giveaway!", ephemeral=True)

    class GiveawayButton(discord.ui.Button):
        def __init__(self, giveaway_id):
            super().__init__(label="🎉", style=discord.ButtonStyle.primary)
            self.giveaway_id = giveaway_id

        async def callback(self, interaction: discord.Interaction):
            giveaways = load_giveaways()
            giveaway = giveaways.get(str(self.giveaway_id))
            if not giveaway:
                await interaction.response.send_message("This giveaway has ended or does not exist.", ephemeral=True)
                return

            user_id = interaction.user.id
            entries = giveaway.get('entries', [])
            if user_id in entries:
                cog = interaction.client.get_cog('AutoGiveaway')
                if not cog:
                    await interaction.response.send_message("Error: Could not load giveaway system.", ephemeral=True)
                    return
                view = discord.ui.View(timeout=60)
                view.add_item(cog.LeaveGiveawayButton(self.giveaway_id, user_id))
                await interaction.response.send_message(
                    "You have already entered! Do you want to leave?",
                    view=view,
                    ephemeral=True
                )
                return

            entries.append(user_id)
            giveaway['entries'] = entries
            giveaways[str(self.giveaway_id)] = giveaway
            save_giveaways(giveaways)

            await interaction.response.send_message("You have successfully entered the giveaway!", ephemeral=True)

    @app_commands.command(name="autogc", description="Start an automatic giveaway (special permission required)")
    @app_commands.describe(
        duration="Duration of the giveaway in seconds",
        prize="Amount of credits to give away",
        winners="Number of winners",
        mention="Role to mention (optional)",
        timing="Start now or nexttime (now/nexttime)"
    )
    async def autogc(self, interaction: discord.Interaction, duration: int, prize: int, winners: int, mention: str = None, timing: str = "now"):
        # 檢查特殊權限
        if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
            return

        # 驗證輸入
        if duration <= 0:
            await interaction.response.send_message("Duration must be a positive integer!", ephemeral=True)
            return
        if prize <= 0:
            await interaction.response.send_message("Prize must be a positive integer!", ephemeral=True)
            return
        if winners <= 0:
            await interaction.response.send_message("Number of winners must be a positive integer!", ephemeral=True)
            return
        if timing not in ["now", "nexttime"]:
            await interaction.response.send_message("Timing must be 'now' or 'nexttime'!", ephemeral=True)
            return

        # 處理 mention
        mention_value = ""
        if mention:
            if mention.lower() == "@everyone":
                mention_value = "@everyone"
            else:
                try:
                    parsed_role = await commands.RoleConverter().convert(interaction, mention)
                    mention_value = f"<@&{parsed_role.id}>"
                except commands.RoleNotFound:
                    await interaction.response.send_message("Invalid role mention!", ephemeral=True)
                    return

        # 計算時間
        current_time = int(time.time())
        first_time = current_time if timing == "now" else current_time + duration
        end_time = first_time + duration

        # 保存抽獎資訊
        giveaways = load_giveaways()
        giveaway_id = str(int(time.time() * 1000))  # 使用時間戳作為唯一 ID
        giveaway_data = {
            "channel": interaction.channel.id,
            "message": 0,  # 初始設為 0，後續更新
            "time": end_time,
            "start_time": current_time,
            "first_time": first_time,
            "mention": mention_value,
            "winners": winners,
            "prize": prize,
            "entries": [],
            "pending": timing == "nexttime",
            "last_count": 0  # 初始參加人數
        }

        # 如果是 now，立即發送第一次抽獎
        if timing == "now":
            message = await self.send_giveaway_message(
                interaction.channel, giveaway_id, mention_value, winners, prize
            )
            giveaway_data['message'] = message.id
            giveaway_data['pending'] = False

        giveaways[giveaway_id] = giveaway_data
        save_giveaways(giveaways)

        await interaction.response.send_message("Giveaway has been set up!", ephemeral=True)

    @app_commands.command(name="autogr", description="Remove an automatic giveaway (special permission required)")
    @app_commands.describe(
        message_id="The message ID of the giveaway to remove"
    )
    async def autogr(self, interaction: discord.Interaction, message_id: str):
        # 檢查特殊權限
        if not has_special_permission(interaction.user.id, [role.id for role in interaction.user.roles]):
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
            return

        try:
            message_id_int = int(message_id)
        except ValueError:
            await interaction.response.send_message("Message ID must be a valid integer!", ephemeral=True)
            return

        giveaways = load_giveaways()
        giveaway_id_to_remove = None
        for giveaway_id, giveaway in giveaways.items():
            if giveaway['message'] == message_id_int:
                giveaway_id_to_remove = giveaway_id
                break

        if giveaway_id_to_remove is None:
            await interaction.response.send_message("No giveaway found with that message ID!", ephemeral=True)
            return

        del giveaways[giveaway_id_to_remove]
        save_giveaways(giveaways)
        await interaction.response.send_message(f"Giveaway with message ID {message_id} has been removed!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoGiveaway(bot))