import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import json
import aiosqlite

# -----------------------------
# Quest definitions
# -----------------------------

QUESTS = [
    {
        "trigger": "slay",
        "reward": 50,
        "description": "A twisted beast emerges from the shadows. First to type **slay** earns $50!"
    },
    {
        "trigger": "gather",
        "reward": 30,
        "description": "Dark herbs sprout under a blood-red moon. First to type **gather** earns $30!"
    },
    {
        "trigger": "hunt",
        "reward": 75,
        "description": "A cursed creature prowls the outskirts. First to type **hunt** earns $75!"
    },
]

# Same rarity system as your Economy/Bossfight
RARITY_BONUS = {
    "common": 10,
    "uncommon": 30,
    "rare": 70,
    "legendary": 120,
    "godlike": 200,
}

QUEST_MIN_DELAY = 300   # seconds
QUEST_MAX_DELAY = 600   # seconds
QUEST_TIMEOUT = 60      # seconds


class Quests(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # guild_id -> quest channel id
        self.guild_channels: dict[int, int] = {}

        # guild_id -> active quest dict
        self.active_quests: dict[int, dict] = {}

        # guild_id -> winner user_id
        self.quest_winners: dict[int, int | None] = {}

        bot.loop.create_task(self.load_settings())
        bot.loop.create_task(self.quest_loop())

    # -----------------------------
    # Database setup
    # -----------------------------

    async def load_settings(self):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS QuestSettings (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER
                )
                """
            )
            await db.commit()

            cursor = await db.execute("SELECT guild_id, channel_id FROM QuestSettings")
            rows = await cursor.fetchall()

            for guild_id, channel_id in rows:
                self.guild_channels[guild_id] = channel_id

    async def set_guild_channel(self, guild_id: int, channel_id: int):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute(
                """
                INSERT INTO QuestSettings (guild_id, channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id
                """,
                (guild_id, channel_id),
            )
            await db.commit()

        self.guild_channels[guild_id] = channel_id

    # -----------------------------
    # Economy helpers
    # -----------------------------

    async def get_user(self, user_id: int):
        async with aiosqlite.connect("economy.db") as db:
            cursor = await db.execute(
                "SELECT money, inventory FROM Economy WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()

            if row is None:
                empty_inv = {}
                await db.execute(
                    "INSERT INTO Economy (user_id, money, inventory) VALUES (?, ?, ?)",
                    (user_id, 100, json.dumps(empty_inv)),
                )
                await db.commit()
                return 100, empty_inv

            money, inventory = row
            return money, json.loads(inventory)

    async def update_user(self, user_id: int, money: int, inventory: dict):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute(
                "UPDATE Economy SET money = ?, inventory = ? WHERE user_id = ?",
                (money, json.dumps(inventory), user_id),
            )
            await db.commit()

    # -----------------------------
    # Reward multiplier
    # -----------------------------

    def reward_multiplier(self, inventory: dict) -> float:
        mult = 1.0

        equipped = inventory.get("equipped", {})

        # Any weapon equipped?
        if equipped.get("weapon"):
            mult += 0.20

        # Any defensive gear equipped?
        if equipped.get("defense"):
            mult += 0.20

        return mult

    # -----------------------------
    # Quest timeout
    # -----------------------------

    async def quest_timeout(self, guild_id: int, quest: dict, channel: discord.TextChannel):
        await asyncio.sleep(QUEST_TIMEOUT)

        if (
            self.active_quests.get(guild_id) == quest
            and self.quest_winners.get(guild_id) is None
        ):
            self.active_quests.pop(guild_id, None)
            self.quest_winners.pop(guild_id, None)
            await channel.send("⌛ **The quest has expired!** Nobody completed it in time.")

    # -----------------------------
    # Quest loop
    # -----------------------------

    async def quest_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            delay = random.randint(QUEST_MIN_DELAY, QUEST_MAX_DELAY)
            await asyncio.sleep(delay)

            for guild_id, channel_id in list(self.guild_channels.items()):
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    continue

                channel = self.bot.get_channel(channel_id)
                if not isinstance(channel, discord.TextChannel):
                    continue

                # Skip if a quest is already active in this guild
                if guild_id in self.active_quests:
                    continue

                quest = random.choice(QUESTS)
                self.active_quests[guild_id] = quest
                self.quest_winners[guild_id] = None

                await channel.send(
                    f"⚔️ **QUEST TIME!**\n"
                    f"{quest['description']}\n"
                    f"Reward: **${quest['reward']}**\n"
                    f"⏱️ First to type **{quest['trigger']}** within {QUEST_TIMEOUT} seconds wins!"
                )

                self.bot.loop.create_task(self.quest_timeout(guild_id, quest, channel))

    # -----------------------------
    # Slash commands
    # -----------------------------

    @app_commands.command(
        name="questsetchannel",
        description="Set the channel where random quests will appear.",
    )
    async def questsetchannel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )

        guild = interaction.guild

        # Allow server owner OR bot owner
        app_info = await self.bot.application_info()
        is_bot_owner = interaction.user.id == app_info.owner.id
        is_guild_owner = interaction.user.id == guild.owner_id

        if not (is_bot_owner or is_guild_owner):
            return await interaction.response.send_message(
                "❌ You must be the **server owner** or **bot owner** to use this command.",
                ephemeral=True,
            )

        await self.set_guild_channel(guild.id, channel.id)
        await interaction.response.send_message(
            f"✅ Quest channel set to {channel.mention}",
            ephemeral=True,
        )

    @app_commands.command(
        name="questtest",
        description="Trigger a test quest in the configured quest channel.",
    )
    async def questtest(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )

        app_info = await self.bot.application_info()
        is_bot_owner = interaction.user.id == app_info.owner.id

        if not is_bot_owner:
            return await interaction.response.send_message(
                "❌ Only the **bot owner** can use this command.",
                ephemeral=True,
            )

        guild_id = interaction.guild.id

        if guild_id not in self.guild_channels:
            return await interaction.response.send_message(
                "❌ Quest channel not set. Use `/questsetchannel` first.",
                ephemeral=True,
            )

        channel = self.bot.get_channel(self.guild_channels[guild_id])
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ Quest channel is invalid.",
                ephemeral=True,
            )

        quest = random.choice(QUESTS)
        self.active_quests[guild_id] = quest
        self.quest_winners[guild_id] = None

        await channel.send(
            f"⚔️ **TEST QUEST!**\n"
            f"{quest['description']}\n"
            f"Reward: **${quest['reward']}**\n"
            f"⏱️ First to type **{quest['trigger']}** within {QUEST_TIMEOUT} seconds wins!"
        )

        self.bot.loop.create_task(self.quest_timeout(guild_id, quest, channel))

        await interaction.response.send_message("✅ Test quest sent.", ephemeral=True)

    # -----------------------------
    # Message listener
    # -----------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        quest = self.active_quests.get(guild_id)

        if not quest:
            return

        if message.content.lower().strip() != quest["trigger"]:
            return

        winner_id = self.quest_winners.get(guild_id)

        # First correct responder wins
        if winner_id is None:
            self.quest_winners[guild_id] = message.author.id

            money, inv = await self.get_user(message.author.id)
            mult = self.reward_multiplier(inv)
            reward = int(quest["reward"] * mult)

            money += reward
            await self.update_user(message.author.id, money, inv)

            await message.channel.send(
                f"🏆 **{message.author.mention} completed the quest first!**\n"
                f"You earned **${reward}** (multiplier applied)."
            )

            self.active_quests.pop(guild_id, None)
            return

        # Anyone after the winner loses money
        if message.author.id != winner_id:
            money, inv = await self.get_user(message.author.id)
            money = max(0, money - 10)
            await self.update_user(message.author.id, money, inv)

            await message.channel.send(
                f"💀 {message.author.mention} was too late and lost **$10**."
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Quests(bot))