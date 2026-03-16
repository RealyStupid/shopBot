import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import json
import aiosqlite

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
# BOSS FLAVOR TEXT
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

# ---------------------------------------------------------
# PLAYER FLAVOR TEXT
# ---------------------------------------------------------

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
        self.players = {}  # user_id -> state dict
        self.turn_order = []
        self.current_turn_index = 0
        self.active = False
        self.joining = True
        self.killing_blow_user_id = None

    def add_player(self, user: discord.Member, base_max_hp: int, inventory: dict):
        if user.id in self.players:
            return
        max_hp = base_max_hp + 20 * inventory.get("potion_maxhp_bonus", 0)
        self.players[user.id] = {
            "user": user,
            "hp": max_hp,
            "max_hp": max_hp,
            "inventory": inventory,
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

#SETUPS
JOIN_DURATION = 60
JOIN_COUNTDOWN_INTERVAL = 20
TURN_TIMEOUT = 30

# ---------------------------------------------------------
# THE MAIN FIGHT
# ---------------------------------------------------------

class BossFightCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fights = {}  # guild_id -> BossFight

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
    # /bossfight COMMAND
    # ---------------------------------------------------------
    @app_commands.command(name="bossfight", description="Start a server-wide boss fight.")
    async def bossfight(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )

        guild_id = interaction.guild.id

        # Prevent multiple fights
        if guild_id in self.fights and (self.fights[guild_id].active or self.fights[guild_id].joining):
            return await interaction.response.send_message(
                "❌ A boss fight is already active or forming in this server.",
                ephemeral=True
            )

        channel = interaction.channel

        # Pick a random boss
        boss = random.choice(BOSSES)
        fight = BossFight(boss, channel)
        self.fights[guild_id] = fight

        # Announce boss
        await interaction.response.send_message(
            f"💀 **A Threat Level {boss['threat']} {boss['name']} has appeared!**\n"
            f"HP: **{boss['hp']}**\n"
            f"Damage: **{boss['damage'][0]}–{boss['damage'][1]}**\n"
            f"Reward: **${boss['reward']}** (+${boss['bonus']} killing blow bonus)\n\n"
            f"Type `join` to enter the fight! You have **{JOIN_DURATION} seconds** to join."
        )

        # Start join countdown
        self.bot.loop.create_task(self.join_countdown(fight, guild_id))

    # ---------------------------------------------------------
    # JOIN COUNTDOWN
    # ---------------------------------------------------------
    async def join_countdown(self, fight: BossFight, guild_id: int):
        remaining = JOIN_DURATION

        while remaining > 0 and fight.joining:
            if remaining in (60, 40, 20):
                await fight.channel.send(
                    f"⏳ **{remaining} seconds** left to join the boss fight! Type `join` to enter!"
                )

            await asyncio.sleep(JOIN_COUNTDOWN_INTERVAL)
            remaining -= JOIN_COUNTDOWN_INTERVAL

        # If joining was manually closed
        if not fight.joining:
            return

        fight.joining = False

        # No players joined
        if len(fight.players) == 0:
            await fight.channel.send("❌ No one joined the boss fight. The boss wanders away...")
            self.fights.pop(guild_id, None)
            return

        await fight.channel.send("⛔ **Joining is now closed!**")

        # Solo or multiplayer
        if len(fight.players) == 1:
            await fight.channel.send("⚔️ **Solo mode activated!** You face the boss alone!")
        else:
            await fight.channel.send("⚔️ **The battle begins!** Turn order has been set.")

        # Start the battle
        fight.start_battle()

        # ---------------------------------------------------------
        # INFO SCREEN
        # ---------------------------------------------------------
        await fight.channel.send(
            "📘 **How to Fight**\n\n"
            "During your turn, type one of the following actions:\n\n"
            "⚔️ `attack` — Deal damage to the boss (sword increases damage)\n"
            "🛡️ `protect` — Reduce incoming damage (shield increases protection)\n"
            "🍎 `apple` — Heal yourself (consumes an apple)\n"
            "🧪 `potion` — Increase your max HP (consumes a potion)\n"
            "🏃 `run` — Leave the fight\n\n"
            f"⏱️ You have **{TURN_TIMEOUT} seconds** to act on your turn."
        )

        # Begin turn loop
        self.bot.loop.create_task(self.turn_loop(fight, guild_id))

    # ---------------------------------------------------------
    # PLAYER JOINING VIA MESSAGE
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        fight = self.fights.get(guild_id)

        # If no fight or not in join phase
        if not fight or not fight.joining:
            return

        # Must be in the same channel
        if message.channel.id != fight.channel.id:
            return

        # Player typed "join"
        if message.content.lower().strip() == "join":
            money, inv = await self.get_user(message.author.id)

            # Permanent potion bonus
            bonus_count = inv.get("potion_maxhp_bonus", 0)
            base_max_hp = 100
            max_hp = base_max_hp + 20 * bonus_count

            fight.add_player(message.author, base_max_hp, inv)

            await message.channel.send(
                f"✅ {message.author.mention} has joined the boss fight! (HP: {max_hp})"
            )

    # ---------------------------------------------------------
    # TURN LOOP
    # ---------------------------------------------------------
    async def turn_loop(self, fight: BossFight, guild_id: int):
        while fight.active:

            # Check win/lose
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

            # ---------------------------------------------------------
            # STAT PANEL
            # ---------------------------------------------------------
            inv = state["inventory"]
            sword = "Yes" if "sword" in inv else "No"
            shield = "Yes" if "shield" in inv else "No"
            apples = inv.get("apple", 0)
            potions = inv.get("potion", 0)

            await fight.channel.send(
                f"🔔 {user.mention} — **it's your turn!**\n\n"
                f"❤️ **HP:** {state['hp']} / {state['max_hp']}\n"
                f"🛡️ **Protecting:** {'Yes' if state['protecting'] else 'No'}\n"
                f"⚔️ **Sword:** {sword}\n"
                f"🛡️ **Shield:** {shield}\n"
                f"🍎 **Apples:** {apples}\n"
                f"🧪 **Potions:** {potions}\n\n"
                "Choose: `attack`, `protect`, `apple`, `potion`, `run`"
            )

            # ---------------------------------------------------------
            # WAIT FOR PLAYER ACTION
            # ---------------------------------------------------------
            try:
                action = await self.wait_for_action(fight, user)
            except asyncio.TimeoutError:
                await fight.channel.send(f"⏳ {user.mention} took too long. **Turn skipped.**")
                fight.next_turn()
                continue

            # ---------------------------------------------------------
            # PROCESS ACTION
            # ---------------------------------------------------------
            await self.process_action(fight, guild_id, user, action)

            # Boss dead?
            if fight.is_boss_dead():
                await self.handle_victory(fight, guild_id)
                return

            # Player died or ran?
            if fight.is_wipe():
                await self.handle_defeat(fight, guild_id)
                return

            # ---------------------------------------------------------
            # NEXT TURN OR BOSS TURN
            # ---------------------------------------------------------
            prev_index = fight.current_turn_index
            next_id = fight.next_turn()

            if next_id is None:
                await self.handle_defeat(fight, guild_id)
                return

            # Boss turn:
            # - If we wrapped around (multiplayer)
            # - OR if there is only one player (solo mode)
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
        state["inventory"] = inventory  # sync

        # -------------------------
        # ATTACK
        # -------------------------
        if action == "attack":
            base_min, base_max = 15, 25
            using_sword = "sword" in inventory

            if using_sword:
                base_min += 5
                base_max += 10

            dmg = random.randint(base_min, base_max)
            fight.boss_hp = max(0, fight.boss_hp - dmg)

            # Killing blow?
            if fight.boss_hp == 0:
                fight.killing_blow_user_id = user.id

            # Flavor text
            if using_sword:
                line = random.choice(PLAYER_FLAVOR["attack_sword"])
            else:
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
                await fight.channel.send(f"🍎 {user.mention} tried to use an apple, but has none!")
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
                await fight.channel.send(
                    line.format(player=user.mention, heal=healed)
                )

        # -------------------------
        # POTION
        # -------------------------
        elif action == "potion":
            potions = inventory.get("potion", 0)
            if potions <= 0:
                await fight.channel.send(f"🧪 {user.mention} tried to use a potion, but has none!")
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

        # Reset protection if not used
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

        # Damage reduction
        reduction = 0.0
        if target_state["protecting"]:
            reduction += 0.3
        if "shield" in target_state["inventory"]:
            reduction += 0.2

        reduction = min(reduction, 0.8)
        final_dmg = max(1, int(dmg * (1 - reduction)))

        target_state["hp"] -= final_dmg
        target_state["protecting"] = False

        # Flavor text selection
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

        # Player death
        if target_state["hp"] <= 0:
            target_state["hp"] = 0
            target_state["alive"] = False

            if target.id in fight.turn_order:
                fight.turn_order.remove(target.id)
                if fight.current_turn_index >= len(fight.turn_order):
                    fight.current_turn_index = 0

            await fight.channel.send(
                f"💀 {target.mention} has **fallen** in battle!"
            )

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

        for state in survivors:
            user = state["user"]
            money, inv = await self.get_user(user.id)
            money += boss["reward"]
            await self.update_user(user.id, money, inv)

        if fight.killing_blow_user_id:
            killer = fight.players[fight.killing_blow_user_id]["user"]
            money, inv = await self.get_user(killer.id)
            money += boss["bonus"]
            await self.update_user(killer.id, money, inv)

            await fight.channel.send(
                f"🏅 {killer.mention} dealt the **killing blow** and earns an extra **${boss['bonus']}**!"
            )

        self.fights.pop(guild_id, None)

    # ---------------------------------------------------------
    # DEFEAT
    # ---------------------------------------------------------
    async def handle_defeat(self, fight: BossFight, guild_id: int):
        fight.active = False
        await fight.channel.send(
            f"💀 The **{fight.boss['name']}** stands victorious. All challengers have fallen or fled..."
        )
        self.fights.pop(guild_id, None)


# ---------------------------------------------------------
# COG SETUP
# ---------------------------------------------------------
async def setup(bot):
    await bot.add_cog(BossFightCog(bot))
