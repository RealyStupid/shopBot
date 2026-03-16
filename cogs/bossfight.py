# bossfight.py
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import json
import aiosqlite

# ---------------------------------------------------------
# IMPORT RARITY BONUSES FROM ECONOMY SYSTEM
# ---------------------------------------------------------

RARITY_BONUS = {
    "common": 0,
    "uncommon": 3,
    "rare": 7,
    "legendary": 12,
    "godlike": 20,
}

WEAPON_TYPES = ["sword", "axe", "dagger", "bow", "staff"]
DEFENSIVE_TYPES = ["shield", "armor"]

BASE_HEALTH = 100
BASE_DAMAGE = 5
BASE_DEFENSE = 0

# ---------------------------------------------------------
# BOSS DEFINITIONS
# ---------------------------------------------------------

BOSSES = [
    {
        "name": "Ogre",
        "threat": 1,
        "hp": 200,
        "damage": (15, 25),
        "reward": 400,
        "bonus": 75
    },
    {
        "name": "Dragon",
        "threat": 2,
        "hp": 350,
        "damage": (25, 40),
        "reward": 800,
        "bonus": 150
    },
    {
        "name": "Demon Lord",
        "threat": 3,
        "hp": 450,
        "damage": (30, 45),
        "reward": 1000,
        "bonus": 150
    },
    {
        "name": "Titan",
        "threat": 4,
        "hp": 600,
        "damage": (40, 60),
        "reward": 1500,
        "bonus": 250
    }
]

# ---------------------------------------------------------
# FLAVOR TEXT
# ---------------------------------------------------------

FLAVOR_TEXT = {
    "generic": [
        "{boss} swings violently at {player}, dealing **{dmg}** damage!",
        "{boss} slams the ground, sending a shockwave into {player} for **{dmg}** damage!",
        "{boss} lunges forward and strikes {player} for **{dmg}** damage!",
        "{boss} roars and smashes {player}, causing **{dmg}** damage!",
        "{boss} charges and body-slams {player}, inflicting **{dmg}** damage!"
    ],

    "Ogre": [
        "The Ogre hurls a massive boulder at {player}, crushing them for **{dmg}** damage!",
        "The Ogre swings its heavy club into {player}, dealing **{dmg}** damage!",
        "The Ogre stomps the ground, knocking {player} back for **{dmg}** damage!"
    ],

    "Dragon": [
        "The Dragon breathes scorching flames at {player}, burning them for **{dmg}** damage!",
        "The Dragon snaps its jaws at {player}, tearing into them for **{dmg}** damage!",
        "The Dragon beats its wings, sending a fiery gust into {player} for **{dmg}** damage!"
    ],

    "Demon Lord": [
        "The Demon Lord unleashes a blast of dark energy at {player}, dealing **{dmg}** damage!",
        "The Demon Lord slashes through the air with shadow claws, striking {player} for **{dmg}** damage!",
        "The Demon Lord whispers a curse, causing {player} to suffer **{dmg}** damage!"
    ],

    "Titan": [
        "The Titan stomps the earth, sending tremors into {player} for **{dmg}** damage!",
        "The Titan swings its colossal fist into {player}, crushing them for **{dmg}** damage!",
        "The Titan rips a chunk of stone from the ground and hurls it at {player} for **{dmg}** damage!"
    ],

    "critical": [
        "💥 **CRITICAL HIT!** {boss} unleashes a devastating blow on {player} for **{dmg}** damage!",
        "⚡ {boss} channels immense power and obliterates {player} for **{dmg}** damage!",
        "🔥 {boss} lands a brutal, bone-shattering strike on {player} for **{dmg}** damage!"
    ]
}

PLAYER_FLAVOR = {
    "attack": [
        "{player} charges forward and strikes the {boss} for **{dmg}** damage!",
        "{player} leaps in and slashes the {boss}, dealing **{dmg}** damage!",
        "{player} swings fiercely at the {boss}, hitting for **{dmg}** damage!",
        "{player} attacks with precision, striking the {boss} for **{dmg}** damage!"
    ],

    "attack_sword": [
        "⚔️ {player}'s sword glows as they slash the {boss} for **{dmg}** damage!",
        "⚔️ {player} swings their sword with force, cutting the {boss} for **{dmg}** damage!",
        "⚔️ {player}'s blade slices through the air, striking the {boss} for **{dmg}** damage!"
    ],

    "protect": [
        "{player} raises their guard, preparing to reduce incoming damage!",
        "{player} braces for impact, ready to withstand the next attack!",
        "{player} takes a defensive stance, minimizing the next hit!"
    ],

    "apple": [
        "🍎 {player} eats an apple and restores **{heal}** HP!",
        "🍎 {player} munches on an apple, recovering **{heal}** HP!",
        "🍎 {player} quickly eats an apple, healing **{heal}** HP!"
    ],

    "potion": [
        "🧪 {player} drinks a potion, increasing their max HP by **20**!",
        "🧪 {player} gulps down a potion, boosting their vitality!",
        "🧪 {player} consumes a potion, feeling stronger and healthier!"
    ],

    "run": [
        "🏃 {player} flees the battle!",
        "🏃 {player} decides this fight isn’t worth dying for and runs!",
        "🏃 {player} escapes from the battlefield!"
    ]
}

# ---------------------------------------------------------
# BOSS FIGHT CLASS
# ---------------------------------------------------------

class BossFight:
    def __init__(self, boss: dict, channel: discord.TextChannel):
        self.boss = boss
        self.channel = channel
        self.boss_hp = boss["hp"]
        self.boss_max_hp = boss["hp"]
        self.players = {}
        self.turn_order = []
        self.current_turn_index = 0
        self.active = False
        self.joining = True
        self.killing_blow_user_id = None

    def add_player(self, user: discord.Member, inventory: dict):
        if user.id in self.players:
            return

        # Load equipped gear
        equipped = inventory.get("equipped", {})
        weapon = equipped.get("weapon")
        defense_item = equipped.get("defense")

        # Base + potion HP bonus
        potion_bonus = inventory.get("potion_maxhp_bonus", 0)
        max_hp = BASE_HEALTH + (20 * potion_bonus)

        self.players[user.id] = {
            "user": user,
            "hp": max_hp,
            "max_hp": max_hp,
            "inventory": inventory,
            "equipped_weapon": weapon,
            "equipped_defense": defense_item,
            "protecting": False,
            "alive": True
        }

    def start_battle(self):
        self.joining = False
        self.active = True
        self.turn_order = [uid for uid in self.players.keys() if self.players[uid]["alive"]]

    def get_current_player_id(self):
        if not self.turn_order:
            return None
        return self.turn_order[self.current_turn_index]

    def next_turn(self):
        if not self.turn_order:
            return None
        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
        return self.get_current_player_id()

    def remove_player(self, user_id: int):
        if user_id in self.players:
            self.players[user_id]["alive"] = False
        if user_id in self.turn_order:
            self.turn_order.remove(user_id)
            if self.current_turn_index >= len(self.turn_order):
                self.current_turn_index = 0

    def alive_players(self):
        return [p for p in self.players.values() if p["alive"]]

    def is_boss_dead(self):
        return self.boss_hp <= 0

    def is_wipe(self):
        return len(self.alive_players()) == 0


JOIN_DURATION = 60
JOIN_COUNTDOWN_INTERVAL = 20
TURN_TIMEOUT = 30

# ---------------------------------------------------------
# MAIN COG
# ---------------------------------------------------------

class BossFightCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fights = {}

    # -----------------------------
    # DB HELPERS
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

    # ---------------------------------------------------------
    # /bossfight
    # ---------------------------------------------------------

    @app_commands.command(name="bossfight", description="Start a server-wide boss fight.")
    async def bossfight(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("Use this in a server.", ephemeral=True)

        guild_id = guild.id

        if guild_id in self.fights and (self.fights[guild_id].active or self.fights[guild_id].joining):
            return await interaction.response.send_message("A boss fight is already active.", ephemeral=True)

        boss = random.choice(BOSSES)
        fight = BossFight(boss, interaction.channel)
        self.fights[guild_id] = fight

        await interaction.response.send_message(
            f"💀 **A Threat Level {boss['threat']} {boss['name']} appears!**\n"
            f"HP: **{boss['hp']}**\n"
            f"Damage: **{boss['damage'][0]}–{boss['damage'][1]}**\n"
            f"Reward: **${boss['reward']}** (+${boss['bonus']} bonus)\n\n"
            f"Type `join` to enter! **{JOIN_DURATION} seconds**."
        )

        self.bot.loop.create_task(self.join_countdown(fight, guild_id))

    # ---------------------------------------------------------
    # JOIN COUNTDOWN
    # ---------------------------------------------------------

    async def join_countdown(self, fight: BossFight, guild_id: int):
        remaining = JOIN_DURATION

        while remaining > 0 and fight.joining:
            if remaining in (60, 40, 20):
                await fight.channel.send(f"⏳ **{remaining} seconds** left to join!")
            await asyncio.sleep(JOIN_COUNTDOWN_INTERVAL)
            remaining -= JOIN_COUNTDOWN_INTERVAL

        fight.joining = False

        if len(fight.players) == 0:
            await fight.channel.send("❌ No one joined. The boss wanders away...")
            self.fights.pop(guild_id, None)
            return

        await fight.channel.send("⛔ Joining closed!")
        fight.start_battle()

        await fight.channel.send(
            "📘 **How to Fight**\n"
            "`attack` — Deal damage (weapon increases damage)\n"
            "`protect` — Reduce incoming damage (armor/shield helps)\n"
            "`apple` — Heal 20 HP\n"
            "`potion` — Increase max HP by 20\n"
            "`run` — Leave the fight\n"
            f"⏱️ **{TURN_TIMEOUT} seconds** per turn."
        )

        self.bot.loop.create_task(self.turn_loop(fight, guild_id))

    # ---------------------------------------------------------
    # PLAYER TYPING "join"
    # ---------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        fight = self.fights.get(guild_id)

        if not fight or not fight.joining:
            return
        if message.channel.id != fight.channel.id:
            return

        if message.content.lower().strip() == "join":
            money, inv = await self.get_user(message.author.id)
            fight.add_player(message.author, inv)

            max_hp = fight.players[message.author.id]["max_hp"]
            await message.channel.send(f"✅ {message.author.mention} joined! (HP: {max_hp})")

    # ---------------------------------------------------------
    # TURN LOOP
    # ---------------------------------------------------------

    async def turn_loop(self, fight: BossFight, guild_id: int):
        while fight.active:

            if fight.is_boss_dead():
                await self.handle_victory(fight, guild_id)
                return

            if fight.is_wipe():
                await self.handle_defeat(fight, guild_id)
                return

            current_id = fight.get_current_player_id()
            if current_id is None:
                await self.handle_defeat(fight, guild_id)
                return

            state = fight.players[current_id]
            user = state["user"]

            if not state["alive"]:
                fight.next_turn()
                continue

            # -------------------------
            # STAT PANEL
            # -------------------------
            weapon = state["equipped_weapon"]
            defense_item = state["equipped_defense"]

            weapon_text = f"{weapon['name']} ({weapon['rarity'].capitalize()})" if weapon else "None"
            defense_text = f"{defense_item['name']} ({defense_item['rarity'].capitalize()})" if defense_item else "None"

            apples = state["inventory"].get("apple", 0)
            potions = state["inventory"].get("potion", 0)

            await fight.channel.send(
                f"🔔 {user.mention}, **your turn!**\n\n"
                f"❤️ HP: {state['hp']} / {state['max_hp']}\n"
                f"🗡️ Weapon: {weapon_text}\n"
                f"🛡️ Defense: {defense_text}\n"
                f"🍎 Apples: {apples}\n"
                f"🧪 Potions: {potions}\n\n"
                "Choose: `attack`, `protect`, `apple`, `potion`, `run`"
            )

            try:
                action = await self.wait_for_action(fight, user)
            except asyncio.TimeoutError:
                await fight.channel.send(f"⏳ {user.mention} took too long. Turn skipped.")
                fight.next_turn()
                continue

            await self.process_action(fight, guild_id, user, action)

            if fight.is_boss_dead():
                await self.handle_victory(fight, guild_id)
                return

            if fight.is_wipe():
                await self.handle_defeat(fight, guild_id)
                return

            prev_index = fight.current_turn_index
            fight.next_turn()

            if len(fight.turn_order) == 1 or fight.current_turn_index < prev_index:
                await self.boss_turn(fight, guild_id)

    # ---------------------------------------------------------
    # WAIT FOR ACTION
    # ---------------------------------------------------------

    async def wait_for_action(self, fight: BossFight, user: discord.Member):
        def check(msg: discord.Message):
            return (
                msg.author.id == user.id
                and msg.channel.id == fight.channel.id
                and msg.content.lower().strip() in ("attack", "protect", "apple", "potion", "run")
            )
        msg = await self.bot.wait_for("message", timeout=TURN_TIMEOUT, check=check)
        return msg.content.lower().strip()

    # ---------------------------------------------------------
    # PROCESS PLAYER ACTION
    # ---------------------------------------------------------

    async def process_action(self, fight: BossFight, guild_id: int, user: discord.Member, action: str):
        state = fight.players[user.id]
        money, inventory = await self.get_user(user.id)
        state["inventory"] = inventory

        # -------------------------
        # ATTACK
        # -------------------------
        if action == "attack":
            weapon = state["equipped_weapon"]
            rarity_bonus = 0

            if weapon:
                rarity_bonus = RARITY_BONUS.get(weapon["rarity"], 0)

            dmg = BASE_DAMAGE + rarity_bonus

            fight.boss_hp = max(0, fight.boss_hp - dmg)

            if fight.boss_hp == 0:
                fight.killing_blow_user_id = user.id

            line = random.choice(PLAYER_FLAVOR["attack"])
            await fight.channel.send(
                line.format(player=user.mention, boss=fight.boss["name"], dmg=dmg)
            )

        # -------------------------
        # PROTECT
        # -------------------------
        elif action == "protect":
            state["protecting"] = True
            line = random.choice(PLAYER_FLAVOR["protect"])
            await fight.channel.send(line.format(player=user.mention))

        # -------------------------
        # APPLE
        # -------------------------
        elif action == "apple":
            apples = inventory.get("apple", 0)
            if apples <= 0:
                await fight.channel.send(f"🍎 {user.mention} has no apples!")
            else:
                heal = 20
                old_hp = state["hp"]
                state["hp"] = min(state["max_hp"], state["hp"] + heal)

                inventory["apple"] = apples - 1
                if inventory["apple"] <= 0:
                    inventory.pop("apple")

                await self.update_user(user.id, money, inventory)

                healed = state["hp"] - old_hp
                line = random.choice(PLAYER_FLAVOR["apple"])
                await fight.channel.send(line.format(player=user.mention, heal=healed))

        # -------------------------
        # POTION
        # -------------------------
        elif action == "potion":
            potions = inventory.get("potion", 0)
            if potions <= 0:
                await fight.channel.send(f"🧪 {user.mention} has no potions!")
            else:
                inventory["potion"] = potions - 1
                if inventory["potion"] <= 0:
                    inventory.pop("potion")

                bonus_count = inventory.get("potion_maxhp_bonus", 0) + 1
                inventory["potion_maxhp_bonus"] = bonus_count

                state["max_hp"] += 20
                state["hp"] = min(state["max_hp"], state["hp"] + 20)

                await self.update_user(user.id, money, inventory)

                line = random.choice(PLAYER_FLAVOR["potion"])
                await fight.channel.send(line.format(player=user.mention))

        # -------------------------
        # RUN
        # -------------------------
        elif action == "run":
            fight.remove_player(user.id)
            line = random.choice(PLAYER_FLAVOR["run"])
            await fight.channel.send(line.format(player=user.mention))
            return

        if action != "protect":
            state["protecting"] = False

    # ---------------------------------------------------------
    # BOSS TURN
    # ---------------------------------------------------------

    async def boss_turn(self, fight: BossFight, guild_id: int):
        if fight.is_boss_dead() or fight.is_wipe():
            return

        target_state = random.choice(fight.alive_players())
        target = target_state["user"]

        dmg_min, dmg_max = fight.boss["damage"]
        dmg = random.randint(dmg_min, dmg_max)

        reduction = 0.0

        if target_state["protecting"]:
            reduction += 0.30

        defense_item = target_state["equipped_defense"]
        if defense_item:
            rarity = defense_item["rarity"]
            rarity_bonus = RARITY_BONUS.get(rarity, 0)
            reduction += (rarity_bonus / 100)

        reduction = min(reduction, 0.80)

        final_dmg = max(1, int(dmg * (1 - reduction)))

        target_state["hp"] -= final_dmg
        target_state["protecting"] = False

        boss_name = fight.boss["name"]

        if final_dmg > dmg_max * 0.75:
            line = random.choice(FLAVOR_TEXT["critical"])
        elif boss_name in FLAVOR_TEXT and random.random() < 0.5:
            line = random.choice(FLAVOR_TEXT[boss_name])
        else:
            line = random.choice(FLAVOR_TEXT["generic"])

        await fight.channel.send(
            line.format(boss=boss_name, player=target.mention, dmg=final_dmg)
        )

        await fight.channel.send(
            f"📊 **{boss_name} Stats**\n"
            f"❤️ HP: {fight.boss_hp} / {fight.boss_max_hp}\n"
            f"⚔️ Damage: {dmg_min}–{dmg_max}"
        )

        await fight.channel.send(
            f"🩸 {target.mention} now has **{target_state['hp']} / {target_state['max_hp']} HP**."
        )

        if target_state["hp"] <= 0:
            target_state["hp"] = 0
            target_state["alive"] = False

            if target.id in fight.turn_order:
                fight.turn_order.remove(target.id)
                if fight.current_turn_index >= len(fight.turn_order):
                    fight.current_turn_index = 0

            await fight.channel.send(f"💀 {target.mention} has fallen!")

        # ---------------------------------------------------------
    # VICTORY
    # ---------------------------------------------------------
    async def handle_victory(self, fight: BossFight, guild_id: int):
        fight.active = False
        survivors = fight.alive_players()
        boss = fight.boss

        await fight.channel.send(
            f"🎉 **The {boss['name']} has been defeated!**\n"
            f"All surviving players earn **${boss['reward']}**!"
        )

        # Reward all survivors
        for state in survivors:
            user = state["user"]
            money, inv = await self.get_user(user.id)
            money += boss["reward"]
            await self.update_user(user.id, money, inv)

        # Killing blow bonus
        if fight.killing_blow_user_id:
            killer = fight.players[fight.killing_blow_user_id]["user"]
            money, inv = await self.get_user(killer.id)
            money += boss["bonus"]
            await self.update_user(killer.id, money, inv)

            await fight.channel.send(
                f"🏅 {killer.mention} dealt the **killing blow** and earns an extra **${boss['bonus']}**!"
            )

        # Cleanup
        self.fights.pop(guild_id, None)

    # ---------------------------------------------------------
    # DEFEAT
    # ---------------------------------------------------------
    async def handle_defeat(self, fight: BossFight, guild_id: int):
        fight.active = False
        boss = fight.boss["name"]

        await fight.channel.send(
            f"💀 The **{boss}** stands victorious. All challengers have fallen or fled..."
        )

        # Cleanup
        self.fights.pop(guild_id, None)

# ---------------------------------------------------------
# COG SETUP
# ---------------------------------------------------------
async def setup(bot):
    await bot.add_cog(BossFightCog(bot))