import discord
from discord.ext import commands, tasks
import os
import asyncio

with open('token.txt', 'r') as f:
    TOKEN = f.read().strip()

intents = discord.Intents.all()
intents.members = True

activity = discord.Game(name="StoreCord v2.0.0")
bot = commands.Bot(command_prefix='/', intents=intents, status=discord.Status.idle, activity=activity)

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    os.system("cls")
    print(f'{bot.user} is online')

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
