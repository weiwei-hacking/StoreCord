import discord
from discord.ext import commands, tasks
import os
import asyncio

with open('token.txt', 'r') as f:
    TOKEN = f.read().strip()

intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name="#1 discord store bot"))
    os.system("cls")
    print(f'{bot.user} is online')

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
