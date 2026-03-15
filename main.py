# Import libraries
import discord
from discord.ext import commands
from discord import app_commands

import utilities.bot_config as config

from db_manager import init_economy_db

import os

class client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=config.INTENTS, application_id=config.APPLICATION_ID)

    async def setup_hook(self):
        # load the cog(s)
        for root, dirs, files in os.walk('./cogs'):
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    ext = path.replace('./', '').replace('/', '.').replace('\\', '.').replace('.py', '')
                    await self.load_extension(ext)
                    print(f"Loaded cog: {ext}")

        # some other setup before start
        await init_economy_db()

    async def on_ready(self):
        print(f'Logged on as {self.user}')

bot = client()

@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx, scope: str = None):
    try:
        if scope == "global":
            synced = await bot.tree.sync()
            await ctx.send(f"Globally synced {len(synced)} commands")
        else:
            synced = await bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"Synced {len(synced)} commands to **{ctx.guild.name}**")

    except Exception as e:
        await ctx.send(f"Error while syncing commands: `{e}`")

bot.run(config.BOT_TOKEN)