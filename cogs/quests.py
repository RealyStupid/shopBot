import discord
from discord.ext import commands
import asyncio
import random
import json
import aiosqlite

QUESTS = [
    {
        "trigger": "slay",
        "reward": 50,
        "description": "A monster appears! First to type **slay** wins $50!"
    },
    {
        "trigger": "gather",
        "reward": 30,
        "description": "Gather herbs! First to type **gather** wins $30!"
    },
    {
        "trigger": "hunt",
        "reward": 75,
        "description": "A wild beast appears! First to type **hunt** wins $75!"
    }
]

class Quests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_quest = None
        self.quest_winner = None
        self.guild_channels = {}  # guild_id -> channel_id

        bot.loop.create_task(self.load_settings())
        bot.loop.create_task(self.quest_loop())

    # -----------------------------
    # Database setup
    # -----------------------------
    async def load_settings(self):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS QuestSettings (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER
                )
            """)
            await db.commit()

            cursor = await db.execute("SELECT guild_id, channel_id FROM QuestSettings")
            rows = await cursor.fetchall()

            for guild_id, channel_id in rows:
                self.guild_channels[guild_id] = channel_id

    async def set_guild_channel(self, guild_id: int, channel_id: int):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("""
                INSERT INTO QuestSettings (guild_id, channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id
            """, (guild_id, channel_id))
            await db.commit()

        self.guild_channels[guild_id] = channel_id

    # -----------------------------
    # Economy helpers
    # -----------------------------
    async def get_user(self, user_id: int):
        async with aiosqlite.connect("economy.db") as db:
            cursor = await db.execute("SELECT money, inventory FROM Economy WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()

            if row is None:
                empty_inv = {}
                await db.execute(
                    "INSERT INTO Economy (user_id, money, inventory) VALUES (?, ?, ?)",
                    (user_id, 100, json.dumps(empty_inv))
                )
                await db.commit()
                return 100, empty_inv

            money, inventory = row
            return money, json.loads(inventory)

    async def update_user(self, user_id: int, money: int, inventory: dict):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute(
                "UPDATE Economy SET money = ?, inventory = ? WHERE user_id = ?",
                (money, json.dumps(inventory), user_id)
            )
            await db.commit()

    # -----------------------------
    # RPG reward multiplier
    # -----------------------------
    def reward_multiplier(self, inventory: dict) -> float:
        mult = 1.0

        if "sword" in inventory:
            mult += 0.2
        if "shield" in inventory:
            mult += 0.2
        if "sword" in inventory and "shield" in inventory:
            mult += 0.3  # total +0.7

        return mult

    # -----------------------------
    # Quest timeout (60 seconds)
    # -----------------------------
    async def quest_timeout(self, quest: dict, channel: discord.TextChannel):
        await asyncio.sleep(60)

        if self.active_quest == quest:
            self.active_quest = None
            self.quest_winner = None
            await channel.send("⌛ **The quest has expired!** Nobody completed it in time.")

    # -----------------------------
    # Quest loop
    # -----------------------------
    async def quest_loop(self):
        await self.bot.wait_until_ready()

        while True:
            await asyncio.sleep(random.randint(120, 300))

            for guild_id, channel_id in self.guild_channels.items():
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue

                quest = random.choice(QUESTS)
                self.active_quest = quest
                self.quest_winner = None

                await channel.send(
                    f"⚔️ **QUEST TIME!**\n{quest['description']}\n"
                    f"Reward: **${quest['reward']}**"
                )

                self.bot.loop.create_task(self.quest_timeout(quest, channel))

    # -----------------------------
    # PREFIX COMMANDS
    # -----------------------------

    @commands.command(name="questsetchannel")
    @commands.guild_only()
    async def questsetchannel(self, ctx, channel: discord.TextChannel):
        # Must be server owner OR bot owner
        if ctx.author.id != ctx.guild.owner_id and ctx.author.id != self.bot.owner_id:
            return await ctx.send("❌ You must be the **server owner** or **bot owner** to use this command.")

        await self.set_guild_channel(ctx.guild.id, channel.id)
        await ctx.send(f"✅ Quest channel set to {channel.mention}")

    @commands.command(name="questtest")
    async def questtest(self, ctx):
        # Bot owner only
        if ctx.author.id != self.bot.owner_id:
            return await ctx.send("❌ Only the **bot owner** can use this command.")

        guild_id = ctx.guild.id

        if guild_id not in self.guild_channels:
            return await ctx.send("❌ Quest channel not set. Use `!questsetchannel` first.")

        channel = self.bot.get_channel(self.guild_channels[guild_id])
        if not channel:
            return await ctx.send("❌ Quest channel is invalid.")

        quest = random.choice(QUESTS)
        self.active_quest = quest
        self.quest_winner = None

        await channel.send(
            f"⚔️ **TEST QUEST!**\n{quest['description']}\n"
            f"Reward: **${quest['reward']}**"
        )

        self.bot.loop.create_task(self.quest_timeout(quest, channel))

        await ctx.send("✅ Test quest sent.")

    # -----------------------------
    # Message listener
    # -----------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not self.active_quest:
            return

        quest = self.active_quest

        if message.content.lower().strip() != quest["trigger"]:
            return

        # First correct responder wins
        if self.quest_winner is None:
            self.quest_winner = message.author

            money, inv = await self.get_user(message.author.id)
            mult = self.reward_multiplier(inv)
            reward = int(quest["reward"] * mult)

            money += reward
            await self.update_user(message.author.id, money, inv)

            await message.channel.send(
                f"🏆 **{message.author.mention} completed the quest first!**\n"
                f"You earned **${reward}** (multiplier applied)."
            )

            self.active_quest = None
            return

        # Anyone after the winner loses money
        if message.author.id != self.quest_winner.id:
            money, inv = await self.get_user(message.author.id)
            money = max(0, money - 10)
            await self.update_user(message.author.id, money, inv)

            await message.channel.send(
                f"💀 {message.author.mention} was too late and lost **$10**."
            )


async def setup(bot):
    await bot.add_cog(Quests(bot))