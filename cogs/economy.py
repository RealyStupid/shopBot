import random
from typing import Dict, List, Optional, Literal

import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import json

from discord.ui import View, Button

# -----------------------------
# Constants & Loot Tables
# -----------------------------

RARITY_ORDER = ["common", "uncommon", "rare", "legendary", "godlike"]

RARITY_BONUS = {
    "common": 10,
    "uncommon": 30,
    "rare": 70,
    "legendary": 120,
    "godlike": 200,
}

CRATE_RARITY_WEIGHTS = {
    "rare": 85,
    "legendary": 14,
    "godlike": 1,
}

WEAPON_TYPES = ["sword", "axe", "dagger", "bow", "staff"]
DEFENSIVE_TYPES = ["shield", "armor"]

SHOP_NAMES = {
    "common": {
        "sword": "Rusty Sword",
        "axe": "Rusty Axe",
        "dagger": "Rusty Dagger",
        "bow": "Old Bow",
        "staff": "Cracked Staff",
        "shield": "Cracked Shield",
        "armor": "Worn Armor",
    },
    "uncommon": {
        "sword": "Steel Sword",
        "axe": "Steel Axe",
        "dagger": "Steel Dagger",
        "bow": "Reinforced Bow",
        "staff": "Oak Staff",
        "shield": "Reinforced Shield",
        "armor": "Sturdy Armor",
    },
}

GOTHIC_LOOT: Dict[str, Dict[str, List[str]]] = {
    "sword": {
        "rare": ["Gravebite", "Ashen Edge", "Wraithslash"],
        "legendary": ["Sanguine Reaver", "Ebonfang", "Dreadspire Blade"],
        "godlike": ["Oblivion Rend", "Voidheart Cleaver", "Deathsong Edge"],
    },
    "axe": {
        "rare": ["Bonecleaver", "Wraithsplitter", "Ashrend"],
        "legendary": ["Sanguine Chopper", "Ebonmaul", "Dreadspire Axe"],
        "godlike": ["Oblivion Splitter", "Voidrend Axe", "Deathhowl Cleaver"],
    },
    "dagger": {
        "rare": ["Gravepoint", "Ashen Stiletto", "Wraithprick"],
        "legendary": ["Sanguine Needle", "Ebonshard", "Dreadspire Fang"],
        "godlike": ["Voidkiss", "Oblivion Thorn", "Deathwhisper Blade"],
    },
    "bow": {
        "rare": ["Gravebow", "Ashen String", "Wraithshot"],
        "legendary": ["Sanguine Longbow", "Ebonstrike", "Dreadspire Bow"],
        "godlike": ["Voidpiercer", "Oblivion Harrow", "Deathwind Bow"],
    },
    "staff": {
        "rare": ["Gravewood Staff", "Ashen Rod", "Wraithbranch"],
        "legendary": ["Sanguine Channeler", "Ebonspire Staff", "Dreadspire Rod"],
        "godlike": ["Voidweaver", "Oblivion Scepter", "Deathchant Staff"],
    },
    "shield": {
        "rare": ["Gravewall", "Wraithguard", "Ashen Bastion"],
        "legendary": ["Sanguine Bulwark", "Ebonplate", "Dreadspire Aegis"],
        "godlike": ["Voidbreaker", "Oblivion Ward", "Deathbound Fortress"],
    },
    "armor": {
        "rare": ["Graveplate", "Ashen Mail", "Wraithhide"],
        "legendary": ["Sanguine Carapace", "Ebonsteel", "Dreadspire Armor"],
        "godlike": ["Voidborn Plate", "Oblivion Shell", "Deathbound Armor"],
    },
}

BASE_HEALTH = 100
BASE_DAMAGE = 5
BASE_DEFENSE = 0

MAX_WEAPONS = 20
MAX_DEFENSE = 20
MAX_CRATES = 10

# -----------------------------
# Inventory helpers
# -----------------------------

def ensure_inventory_structure(inv: dict) -> dict:
    if not isinstance(inv, dict):
        inv = {}

    inv.setdefault("consumables", {})
    inv["consumables"].setdefault("apple", 0)
    inv["consumables"].setdefault("potion", 0)

    inv.setdefault("equipment", {})
    for t in WEAPON_TYPES + DEFENSIVE_TYPES:
        inv["equipment"].setdefault(t, [])

    inv.setdefault("equipped", {})
    inv["equipped"].setdefault("weapon", None)
    inv["equipped"].setdefault("defense", None)

    inv.setdefault("crates", 0)

    return inv


def get_rarity_bonus(rarity: str) -> int:
    return RARITY_BONUS.get(rarity, 0)


def compute_stats(inv: dict) -> Dict[str, int]:
    inv = ensure_inventory_structure(inv)
    weapon = inv["equipped"].get("weapon")
    defense = inv["equipped"].get("defense")

    damage_bonus = get_rarity_bonus(weapon["rarity"]) if weapon else 0
    defense_bonus = get_rarity_bonus(defense["rarity"]) if defense else 0

    return {
        "health": BASE_HEALTH,
        "damage": BASE_DAMAGE + damage_bonus,
        "defense": BASE_DEFENSE + defense_bonus,
    }


def roll_rarity() -> str:
    total = sum(CRATE_RARITY_WEIGHTS.values())
    r = random.randint(1, total)
    cumulative = 0
    for rarity, weight in CRATE_RARITY_WEIGHTS.items():
        cumulative += weight
        if r <= cumulative:
            return rarity
    return "rare"


def roll_item_count() -> int:
    return random.choice([2, 3])


def roll_item_type() -> str:
    if random.random() < 0.5:
        return random.choice(WEAPON_TYPES)
    else:
        return random.choice(DEFENSIVE_TYPES)


def generate_crate_item() -> Dict[str, str]:
    rarity = roll_rarity()
    item_type = roll_item_type()
    name = random.choice(GOTHIC_LOOT[item_type][rarity])
    return {"type": item_type, "name": name, "rarity": rarity}


def format_item_line(item: Dict[str, str]) -> str:
    return f"{item['name']} ({item['rarity'].capitalize()})"


def item_matches_slot(item_type: str, slot: str) -> bool:
    if slot == "weapon":
        return item_type in WEAPON_TYPES
    if slot == "defense":
        return item_type in DEFENSIVE_TYPES
    return False


def item_display_for_autocomplete(item: Dict) -> str:
    rarity = item["rarity"].upper()
    t = item["type"].capitalize()
    bonus = get_rarity_bonus(item["rarity"])
    if item["type"] in WEAPON_TYPES:
        return f"{item['name']} — {rarity} {t} — DMG: +{bonus}"
    else:
        return f"{item['name']} — {rarity} {t} — DEF: +{bonus}"

def count_weapons(inv):
    return sum(len(inv["equipment"][t]) for t in WEAPON_TYPES)

def count_defense(inv):
    return sum(len(inv["equipment"][t]) for t in DEFENSIVE_TYPES)

def can_add_equipment(inv, item_type):
    if item_type in WEAPON_TYPES:
        return count_weapons(inv) < MAX_WEAPONS
    if item_type in DEFENSIVE_TYPES:
        return count_defense(inv) < MAX_DEFENSE
    return False

def can_add_crate(inv):
    return inv["crates"] < MAX_CRATES

# -----------------------------
# Pagination View for /profile
# -----------------------------

class ProfileView(View):
    def __init__(self, pages, owner: discord.User):
        super().__init__(timeout=60)
        self.pages = pages
        self.index = 0
        self.owner = owner

        prev_btn = Button(label="◀ Previous", style=discord.ButtonStyle.secondary)
        next_btn = Button(label="Next ▶", style=discord.ButtonStyle.secondary)

        async def prev_callback(interaction: discord.Interaction):
            if interaction.user.id != self.owner.id:
                return await interaction.response.send_message(
                    "This isn't your profile.", ephemeral=True
                )
            self.index = (self.index - 1) % len(self.pages)
            await interaction.response.edit_message(embed=self.pages[self.index], view=self)

        async def next_callback(interaction: discord.Interaction):
            if interaction.user.id != self.owner.id:
                return await interaction.response.send_message(
                    "This isn't your profile.", ephemeral=True
                )
            self.index = (self.index + 1) % len(self.pages)
            await interaction.response.edit_message(embed=self.pages[self.index], view=self)

        prev_btn.callback = prev_callback
        next_btn.callback = next_callback

        self.add_item(prev_btn)
        self.add_item(next_btn)


# -----------------------------
# Economy Cog
# -----------------------------

class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.loop.create_task(self.init_db())

    # -----------------------------
    # DB helpers
    # -----------------------------

    async def init_db(self):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS Economy (
                    user_id INTEGER PRIMARY KEY,
                    money INTEGER,
                    inventory TEXT
                )
                """
            )
            await db.commit()

    async def get_user(self, user_id: int):
        async with aiosqlite.connect("economy.db") as db:
            cursor = await db.execute(
                "SELECT money, inventory FROM Economy WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()

            if row is None:
                inv = ensure_inventory_structure({})
                await db.execute(
                    "INSERT INTO Economy (user_id, money, inventory) VALUES (?, ?, ?)",
                    (user_id, 0, json.dumps(inv)),
                )
                await db.commit()
                return 0, inv

            money, inv_json = row
            inv = ensure_inventory_structure(json.loads(inv_json))
            return money, inv

    async def update_user(self, user_id: int, money: int, inventory: dict):
        inventory = ensure_inventory_structure(inventory)
        async with aiosqlite.connect("economy.db") as db:
            await db.execute(
                "INSERT INTO Economy (user_id, money, inventory) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET money = excluded.money, inventory = excluded.inventory",
                (user_id, money, json.dumps(inventory)),
            )
            await db.commit()

    # -----------------------------
    # /profile (Paginated)
    # -----------------------------

    @app_commands.command(name="profile", description="View your profile, stats, and inventory.")
    async def profile(self, interaction: discord.Interaction):
        user = interaction.user
        user_id = user.id
        money, inv = await self.get_user(user_id)
        stats = compute_stats(inv)

        equipped = inv.get("equipped", {})
        weapon = equipped.get("weapon")
        defense = equipped.get("defense")

        cons = inv.get("consumables", {})
        equipment = inv.get("equipment", {})
        crates = inv.get("crates", 0)

        # -------------------------
        # PAGE 1 — STATS & EQUIPPED
        # -------------------------
        embed1 = discord.Embed(
            title=f"{user.display_name}'s Profile — Stats",
            color=discord.Color.dark_red(),
        )
        embed1.add_field(name="💰 Balance", value=f"${money}", inline=False)
        embed1.add_field(
            name="🩸 Stats",
            value=(
                f"❤️ Health: {stats['health']}\n"
                f"🗡️ Damage: {stats['damage']}\n"
                f"🛡️ Defense: {stats['defense']}"
            ),
            inline=False,
        )

        equipped_lines = []
        if weapon:
            w_bonus = get_rarity_bonus(weapon["rarity"])
            equipped_lines.append(
                f"🗡️ {weapon['name']} ({weapon['rarity'].capitalize()} {weapon['type'].capitalize()}) — DMG +{w_bonus}"
            )
        else:
            equipped_lines.append("🗡️ Weapon: None")

        if defense:
            d_bonus = get_rarity_bonus(defense["rarity"])
            equipped_lines.append(
                f"🛡️ {defense['name']} ({defense['rarity'].capitalize()} {defense['type'].capitalize()}) — DEF +{d_bonus}"
            )
        else:
            equipped_lines.append("🛡️ Defense: None")

        embed1.add_field(
            name="✨ Equipped",
            value="\n".join(equipped_lines)[:1024],
            inline=False,
        )

        # -------------------------
        # PAGE 2 — EQUIPMENT
        # -------------------------
        embed2 = discord.Embed(
            title=f"{user.display_name}'s Profile — Equipment",
            color=discord.Color.dark_red(),
        )

        eq_blocks = []
        for t in WEAPON_TYPES + DEFENSIVE_TYPES:
            items = equipment.get(t, [])
            if not items:
                continue
            header = f"**{t.capitalize()}s:**"
            lines = [header]
            for item in items:
                lines.append(f"• {format_item_line(item)}")
            block = "\n".join(lines)
            eq_blocks.append(block)

        if not eq_blocks:
            eq_blocks.append("No equipment owned yet.")

        eq_text = "\n\n".join(eq_blocks)
        embed2.add_field(
            name="⚔️ Equipment",
            value=eq_text[:1024],
            inline=False,
        )

        # -------------------------
        # PAGE 3 — INVENTORY
        # -------------------------
        embed3 = discord.Embed(
            title=f"{user.display_name}'s Profile — Inventory",
            color=discord.Color.dark_red(),
        )

        cons_lines = []
        for k, v in cons.items():
            if v > 0:
                emoji = "🍎" if k == "apple" else "🧪" if k == "potion" else "🎒"
                cons_lines.append(f"{emoji} {k.capitalize()} × {v}")
        if not cons_lines:
            cons_lines.append("None")

        crates_text = f"🎁 Dark Crates × {crates}" if crates > 0 else "None"

        embed3.add_field(
            name="🎒 Consumables",
            value="\n".join(cons_lines)[:1024],
            inline=False,
        )
        embed3.add_field(
            name="🎁 Crates",
            value=crates_text[:1024],
            inline=False,
        )

        pages = [embed1, embed2, embed3]
        view = ProfileView(pages, user)

        await interaction.response.send_message(embed=embed1, view=view)

    # -----------------------------
    # Shop
    # -----------------------------

    @app_commands.command(name="shop", description="View the shop (common & uncommon gear, consumables).")
    async def shop(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛒 Shop",
            description="Common & Uncommon gear and consumables.",
            color=discord.Color.gold(),
        )

        gear_lines = []
        for rarity in ["common", "uncommon"]:
            lines = [f"**{rarity.capitalize()} Gear:**"]
            for t in WEAPON_TYPES + DEFENSIVE_TYPES:
                name = SHOP_NAMES[rarity][t]
                cost = 50 if rarity == "common" else 150
                lines.append(f"• {name} ({t.capitalize()}) — ${cost}")
            gear_lines.append("\n".join(lines))

        embed.add_field(name="⚔️ Gear", value="\n\n".join(gear_lines), inline=False)
        embed.add_field(
            name="🎒 Consumables",
            value="• Apple — $10\n• Potion — $50",
            inline=False,
        )
        embed.add_field(
            name="🎁 Crates",
            value="• Dark Crate — $250 (2–3 Rare+ items)",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    # -----------------------------
    # /buy Autocomplete
    # -----------------------------

    async def buy_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        choices = []

        # --- Common & Uncommon Gear ---
        for rarity in ["common", "uncommon"]:
            for t in WEAPON_TYPES + DEFENSIVE_TYPES:
                name = SHOP_NAMES[rarity][t]
                display = f"[{rarity.capitalize()}] {name}"
                if current.lower() in display.lower():
                    choices.append(app_commands.Choice(name=display, value=name))
                if len(choices) >= 25:
                    return choices

        # --- Consumables ---
        consumables = {
            "Apple": "apple",
            "Potion": "potion",
        }
        for display, key in consumables.items():
            full = f"[Consumable] {display}"
            if current.lower() in full.lower():
                choices.append(app_commands.Choice(name=full, value=key))
            if len(choices) >= 25:
                return choices

        # --- Crate ---
        crate_display = "[Crate] Dark Crate"
        if current.lower() in crate_display.lower():
            choices.append(app_commands.Choice(name=crate_display, value="dark_crate"))

        return choices

    # -----------------------------
    # /buy
    # -----------------------------

    @app_commands.command(name="buy", description="Buy an item from the shop.")
    @app_commands.autocomplete(item_name=buy_autocomplete)
    @app_commands.describe(
        item_name="The item you want to buy.",
        quantity="How many (only for consumables)."
    )
    async def buy(self, interaction: discord.Interaction, item_name: str, quantity: Optional[int] = 1):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)

        # -------------------------
        # 1. Gear (Common/Uncommon)
        # -------------------------
        for rarity in ["common", "uncommon"]:
            for t in WEAPON_TYPES + DEFENSIVE_TYPES:
                shop_name = SHOP_NAMES[rarity][t]
                if item_name == shop_name:

                    # INVENTORY LIMIT CHECK
                    if not can_add_equipment(inv, t):
                        limit = MAX_WEAPONS if t in WEAPON_TYPES else MAX_DEFENSE
                        return await interaction.response.send_message(
                            f"Your **{t}** inventory is full (max {limit}). Sell something first.",
                            ephemeral=True
                        )

                    cost = 50 if rarity == "common" else 150

                    if money < cost:
                        return await interaction.response.send_message(
                            "You don't have enough money.", ephemeral=True
                        )

                    money -= cost
                    inv["equipment"][t].append({"name": shop_name, "rarity": rarity})

                    await self.update_user(user_id, money, inv)
                    return await interaction.response.send_message(
                        f"You bought **{shop_name}** ({rarity.capitalize()} {t.capitalize()}) for ${cost}."
                    )

        # -------------------------
        # 2. Consumables
        # -------------------------
        consumable_map = {
            "apple": ("Apple", 10),
            "potion": ("Potion", 50),
        }

        if item_name in consumable_map:
            display_name, cost_per = consumable_map[item_name]

            if quantity < 1:
                return await interaction.response.send_message(
                    "Quantity must be at least 1.", ephemeral=True
                )

            total_cost = cost_per * quantity

            if money < total_cost:
                return await interaction.response.send_message(
                    f"You need ${total_cost}, but you only have ${money}.",
                    ephemeral=True,
                )

            money -= total_cost
            inv["consumables"][item_name] = inv["consumables"].get(item_name, 0) + quantity

            await self.update_user(user_id, money, inv)
            return await interaction.response.send_message(
                f"You bought **{quantity}× {display_name}** for ${total_cost}."
            )

        # -------------------------
        # 3. Crates
        # -------------------------
        if item_name == "dark_crate":

            if not can_add_crate(inv):
                return await interaction.response.send_message(
                    f"You cannot hold more crates (max {MAX_CRATES}).",
                    ephemeral=True
                )

            cost = 250

            if money < cost:
                return await interaction.response.send_message(
                    "You don't have enough money for a Dark Crate.", ephemeral=True
                )

            money -= cost
            inv["crates"] += 1

            await self.update_user(user_id, money, inv)
            return await interaction.response.send_message(
                "You bought **1 Dark Crate** for $250."
            )

        # -------------------------
        # 4. Invalid item
        # -------------------------
        return await interaction.response.send_message(
            "That item is not sold in the shop.", ephemeral=True
        )

    # -----------------------------
    # /sell autocomplete
    # -----------------------------

    async def sell_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        user_id = interaction.user.id
        _, inv = await self.get_user(user_id)
        inv = ensure_inventory_structure(inv)

        choices = []

        # -------------------------
        # Gear (weapons + defense)
        # -------------------------
        for t, items in inv["equipment"].items():
            for item in items:
                display = f"[{item['rarity'].capitalize()}] {item['name']} ({t.capitalize()})"
                if current.lower() in display.lower():
                    choices.append(app_commands.Choice(name=display, value=item["name"]))
                if len(choices) >= 25:
                    return choices

        # -------------------------
        # Consumables
        # -------------------------
        consumable_map = {
            "apple": "Apple",
            "potion": "Potion",
        }

        for key, display in consumable_map.items():
            if inv["consumables"].get(key, 0) > 0:
                full = f"[Consumable] {display}"
                if current.lower() in full.lower():
                    choices.append(app_commands.Choice(name=full, value=key))
                if len(choices) >= 25:
                    return choices

        # -------------------------
        # Crates
        # -------------------------
        if inv["crates"] > 0:
            crate_display = "[Crate] Dark Crate"
            if current.lower() in crate_display.lower():
                choices.append(app_commands.Choice(name=crate_display, value="dark_crate"))

        return choices

    # -----------------------------
    # Crates
    # -----------------------------

    @app_commands.command(name="opencrate", description="Open one of your Dark Crates.")
    async def opencrate(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)

        if inv["crates"] <= 0:
            await interaction.response.send_message(
                "You don't have any crates to open.",
                ephemeral=True
            )
            return

        # Remove 1 crate
        inv["crates"] -= 1

        count = roll_item_count()
        obtained = []

        for _ in range(count):
            item = generate_crate_item()
            item_type = item["type"]

            # -----------------------------
            # INVENTORY LIMIT CHECK
            # -----------------------------
            if not can_add_equipment(inv, item_type):
                # Stop giving items once full
                break

            # Add item
            inv["equipment"][item_type].append({
                "name": item["name"],
                "rarity": item["rarity"]
            })
            obtained.append(item)

        await self.update_user(user_id, money, inv)

        # Build result text
        if obtained:
            lines = [
                f"• {item['name']} ({item['rarity'].capitalize()} {item['type'].capitalize()})"
                for item in obtained
            ]
            description = (
                f"You received **{len(obtained)}** item(s):\n" +
                "\n".join(lines)
            )
        else:
            description = (
                "Your inventory is full — no items could be added.\n"
                "Sell some equipment and try again."
            )

        embed = discord.Embed(
            title="🎁 Dark Crate Opened",
            description=description,
            color=discord.Color.dark_purple(),
        )

        await interaction.response.send_message(embed=embed)

    # -----------------------------
    # Equipment (View All)
    # -----------------------------

    @app_commands.command(name="equipment", description="View all your equipment.")
    async def equipment(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Equipment",
            color=discord.Color.dark_red(),
        )

        eq_lines = []
        for t in WEAPON_TYPES + DEFENSIVE_TYPES:
            items = inv["equipment"].get(t, [])
            if not items:
                continue
            header = f"**{t.capitalize()}s:**"
            lines = [header]
            for item in items:
                lines.append(f"• {format_item_line(item)}")
            eq_lines.append("\n".join(lines))

        if not eq_lines:
            eq_lines.append("You don't own any equipment yet.")

        embed.description = "\n\n".join(eq_lines)
        await interaction.response.send_message(embed=embed)

    # -----------------------------
    # /sell command
    # -----------------------------

    @app_commands.command(name="sell", description="Sell an item from your inventory.")
    @app_commands.autocomplete(item_name=sell_autocomplete)
    @app_commands.describe(
        item_name="The item you want to sell.",
        quantity="How many (only for consumables)."
    )
    async def sell(
        self,
        interaction: discord.Interaction,
        item_name: str,
        quantity: Optional[int] = 1,
    ):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)
        inv = ensure_inventory_structure(inv)

        # -------------------------
        # 1. Gear (weapons + defense)
        # -------------------------
        for t, items in inv["equipment"].items():
            for item in items:
                if item["name"] == item_name:

                    # Determine sell price (50% of buy price)
                    rarity = item["rarity"]
                    buy_price = 50 if rarity == "common" else 150 if rarity == "uncommon" else None

                    # Crate gear (rare+) has no buy price → use rarity table
                    if buy_price is None:
                        rarity_sell = {
                            "rare": 150,
                            "legendary": 300,
                            "godlike": 500,
                        }
                        sell_price = rarity_sell[rarity]
                    else:
                        sell_price = buy_price // 2

                    # Remove item
                    inv["equipment"][t].remove(item)
                    money += sell_price

                    await self.update_user(user_id, money, inv)
                    return await interaction.response.send_message(
                        f"You sold **{item_name}** ({rarity.capitalize()} {t.capitalize()}) for **${sell_price}**."
                    )

        # -------------------------
        # 2. Consumables
        # -------------------------
        consumable_map = {
            "apple": ("Apple", 10),
            "potion": ("Potion", 50),
        }

        if item_name in consumable_map:
            display_name, buy_price = consumable_map[item_name]

            if quantity < 1:
                return await interaction.response.send_message(
                    "Quantity must be at least 1.",
                    ephemeral=True
                )

            owned = inv["consumables"].get(item_name, 0)
            if owned < quantity:
                return await interaction.response.send_message(
                    f"You only have **{owned}× {display_name}**.",
                    ephemeral=True
                )

            sell_price = (buy_price // 2) * quantity

            inv["consumables"][item_name] -= quantity
            money += sell_price

            await self.update_user(user_id, money, inv)
            return await interaction.response.send_message(
                f"You sold **{quantity}× {display_name}** for **${sell_price}**."
            )

        # -------------------------
        # 3. Crates
        # -------------------------
        if item_name == "dark_crate":
            if inv["crates"] <= 0:
                return await interaction.response.send_message(
                    "You don't have any crates to sell.",
                    ephemeral=True
                )

            sell_price = 250 // 2  # 50% of buy price = 125

            inv["crates"] -= 1
            money += sell_price

            await self.update_user(user_id, money, inv)
            return await interaction.response.send_message(
                f"You sold **1 Dark Crate** for **${sell_price}**."
            )

        # -------------------------
        # 4. Invalid item
        # -------------------------
        return await interaction.response.send_message(
            "You don't own that item.",
            ephemeral=True
        )

    # -----------------------------
    # Loadout (Equipped Items)
    # -----------------------------

    @app_commands.command(name="loadout", description="View your currently equipped gear.")
    async def loadout(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)
        stats = compute_stats(inv)

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Loadout",
            color=discord.Color.dark_red(),
        )

        weapon = inv["equipped"].get("weapon")
        defense = inv["equipped"].get("defense")

        if weapon:
            w_bonus = get_rarity_bonus(weapon["rarity"])
            w_text = f"{weapon['name']} ({weapon['rarity'].capitalize()} {weapon['type'].capitalize()}) — DMG +{w_bonus}"
        else:
            w_text = "None"

        if defense:
            d_bonus = get_rarity_bonus(defense["rarity"])
            d_text = f"{defense['name']} ({defense['rarity'].capitalize()} {defense['type'].capitalize()}) — DEF +{d_bonus}"
        else:
            d_text = "None"

        embed.add_field(name="🗡️ Weapon", value=w_text, inline=False)
        embed.add_field(name="🛡️ Defense", value=d_text, inline=False)
        embed.add_field(
            name="🩸 Stats",
            value=(
                f"❤️ Health: {stats['health']}\n"
                f"🗡️ Damage: {stats['damage']}\n"
                f"🛡️ Defense: {stats['defense']}"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    # -----------------------------
    # Equip / Unequip (with autocomplete)
    # -----------------------------

    async def equip_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:

        user_id = interaction.user.id
        _, inv = await self.get_user(user_id)
        inv = ensure_inventory_structure(inv)

        slot = getattr(interaction.namespace, "slot", None)

        if slot not in ["weapon", "defense"]:
            return []

        choices: List[app_commands.Choice[str]] = []

        for t, items in inv["equipment"].items():
            for item in items:
                if not item_matches_slot(t, slot):
                    continue

                display = item_display_for_autocomplete({"type": t, **item})

                if current.lower() in display.lower():
                    choices.append(app_commands.Choice(name=display, value=item["name"]))

                if len(choices) >= 25:
                    break
            if len(choices) >= 25:
                break

        return choices

    @app_commands.command(name="equip", description="Equip a weapon or defensive item.")
    @app_commands.describe(
        slot="Which slot to equip to (weapon or defense).",
        item_name="Choose an item from your inventory.",
    )
    @app_commands.choices(
        slot=[
            app_commands.Choice(name="Weapon", value="weapon"),
            app_commands.Choice(name="Defense", value="defense"),
        ]
    )
    @app_commands.autocomplete(item_name=equip_autocomplete)
    async def equip(
        self,
        interaction: discord.Interaction,
        slot: app_commands.Choice[str],
        item_name: str,
    ):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)
        inv = ensure_inventory_structure(inv)

        slot_value = slot.value

        found_item = None
        found_type = None
        for t, items in inv["equipment"].items():
            for item in items:
                if item["name"] == item_name and item_matches_slot(t, slot_value):
                    found_item = item
                    found_type = t
                    break
            if found_item:
                break

        if not found_item:
            await interaction.response.send_message(
                "You don't own that item or it doesn't fit that slot.",
                ephemeral=True,
            )
            return

        inv["equipped"][slot_value] = {
            "type": found_type,
            "name": found_item["name"],
            "rarity": found_item["rarity"],
        }

        await self.update_user(user_id, money, inv)

        bonus = get_rarity_bonus(found_item["rarity"])
        stat_label = f"DMG +{bonus}" if slot_value == "weapon" else f"DEF +{bonus}"

        await interaction.response.send_message(
            f"You equipped **{found_item['name']}** ({found_item['rarity'].capitalize()} {found_type.capitalize()}) "
            f"to your **{slot_value}** slot — {stat_label}."
        )

    @app_commands.command(name="unequip", description="Unequip your weapon or defensive item.")
    @app_commands.choices(
        slot=[
            app_commands.Choice(name="Weapon", value="weapon"),
            app_commands.Choice(name="Defense", value="defense"),
        ]
    )
    async def unequip(self, interaction: discord.Interaction, slot: app_commands.Choice[str]):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)
        inv = ensure_inventory_structure(inv)

        slot_value = slot.value

        if not inv["equipped"].get(slot_value):
            await interaction.response.send_message(
                f"You have nothing equipped in your {slot_value} slot.",
                ephemeral=True,
            )
            return

        inv["equipped"][slot_value] = None
        await self.update_user(user_id, money, inv)

        await interaction.response.send_message(f"You unequipped your **{slot_value}** slot.")

    # -----------------------------
    # Debug money command
    # -----------------------------

    @app_commands.command(name="givemoney", description="[Debug] Give yourself money.")
    @commands.is_owner()
    async def givemoney(self, interaction: discord.Interaction, amount: int, user: discord.User):
        user_id = user.id
        money, inv = await self.get_user(user_id)
        money += amount
        await self.update_user(user_id, money, inv)
        await interaction.response.send_message(
            f"Gave {user.mention} ${amount}. New balance: ${money}."
        )

# -----------------------------
# Cog Setup
# -----------------------------

async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))