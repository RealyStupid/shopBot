# cogs/economy.py
import random
from typing import Dict, List, Optional, Literal

import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import json

# -----------------------------
# Constants & Loot Tables
# -----------------------------

RARITY_ORDER = ["common", "uncommon", "rare", "legendary", "godlike"]

RARITY_BONUS = {
    "common": 0,
    "uncommon": 3,
    "rare": 7,
    "legendary": 12,
    "godlike": 20,
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


# -----------------------------
# Economy Cog (DB-backed)
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
    # /profile
    # -----------------------------

    @app_commands.command(name="profile", description="View your profile, stats, and inventory.")
    async def profile(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)
        stats = compute_stats(inv)

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Profile",
            color=discord.Color.dark_red(),
        )

        embed.add_field(name="💰 Balance", value=f"${money}", inline=False)

        embed.add_field(
            name="🩸 Stats",
            value=(
                f"❤️ Health: {stats['health']}\n"
                f"🗡️ Damage: {stats['damage']}\n"
                f"🛡️ Defense: {stats['defense']}"
            ),
            inline=False,
        )

        cons = inv["consumables"]
        cons_lines = []
        if cons.get("apple", 0) > 0:
            cons_lines.append(f"🍎 Apple × {cons['apple']}")
        if cons.get("potion", 0) > 0:
            cons_lines.append(f"🧪 Potion × {cons['potion']}")
        if not cons_lines:
            cons_lines.append("None")
        embed.add_field(name="🎒 Consumables", value="\n".join(cons_lines), inline=False)

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
            eq_lines.append("No equipment owned yet.")
        embed.add_field(name="⚔️ Equipment", value="\n\n".join(eq_lines), inline=False)

        equipped_lines = []
        weapon = inv["equipped"].get("weapon")
        defense = inv["equipped"].get("defense")

        if weapon:
            bonus = get_rarity_bonus(weapon["rarity"])
            equipped_lines.append(
                f"🗡️ Weapon: {weapon['name']} ({weapon['rarity'].capitalize()}) — DMG +{bonus}"
            )
        else:
            equipped_lines.append("🗡️ Weapon: None")

        if defense:
            bonus = get_rarity_bonus(defense["rarity"])
            equipped_lines.append(
                f"🛡️ Defense: {defense['name']} ({defense['rarity'].capitalize()}) — DEF +{bonus}"
            )
        else:
            equipped_lines.append("🛡️ Defense: None")

        embed.add_field(name="✨ Equipped", value="\n".join(equipped_lines), inline=False)

        await interaction.response.send_message(embed=embed)

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

    @app_commands.command(name="buy", description="Buy an item from the shop.")
    @app_commands.describe(
        category="What are you buying?",
        item_type="Type of gear (if buying gear).",
        rarity="Rarity (common/uncommon) for gear.",
        consumable="Consumable name if buying consumables.",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Gear", value="gear"),
            app_commands.Choice(name="Consumable", value="consumable"),
            app_commands.Choice(name="Crate", value="crate"),
        ]
    )
    async def buy(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        item_type: Optional[Literal["sword", "axe", "dagger", "bow", "staff", "shield", "armor"]] = None,
        rarity: Optional[Literal["common", "uncommon"]] = None,
        consumable: Optional[Literal["apple", "potion"]] = None,
    ):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)

        if category.value == "gear":
            if not item_type or not rarity:
                await interaction.response.send_message("You must specify item_type and rarity for gear.", ephemeral=True)
                return
            name = SHOP_NAMES[rarity][item_type]
            cost = 50 if rarity == "common" else 150
            if money < cost:
                await interaction.response.send_message("You don't have enough money.", ephemeral=True)
                return
            money -= cost
            inv["equipment"][item_type].append({"name": name, "rarity": rarity})
            await self.update_user(user_id, money, inv)
            await interaction.response.send_message(
                f"You bought **{name}** ({rarity.capitalize()} {item_type.capitalize()}) for ${cost}."
            )

        elif category.value == "consumable":
            if not consumable:
                await interaction.response.send_message("You must specify which consumable to buy.", ephemeral=True)
                return
            cost = 10 if consumable == "apple" else 50
            if money < cost:
                await interaction.response.send_message("You don't have enough money.", ephemeral=True)
                return
            money -= cost
            inv["consumables"][consumable] = inv["consumables"].get(consumable, 0) + 1
            await self.update_user(user_id, money, inv)
            await interaction.response.send_message(f"You bought 1 **{consumable}** for ${cost}.")

        elif category.value == "crate":
            cost = 250
            if money < cost:
                await interaction.response.send_message("You don't have enough money for a crate.", ephemeral=True)
                return
            money -= cost
            inv["crates"] += 1
            await self.update_user(user_id, money, inv)
            await interaction.response.send_message("You bought 1 **Dark Crate** for $250.")

    # -----------------------------
    # Crates
    # -----------------------------

    @app_commands.command(name="opencrate", description="Open one of your Dark Crates.")
    async def opencrate(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        money, inv = await self.get_user(user_id)

        if inv["crates"] <= 0:
            await interaction.response.send_message("You don't have any crates to open.", ephemeral=True)
            return

        inv["crates"] -= 1

        count = roll_item_count()
        obtained = []
        for _ in range(count):
            item = generate_crate_item()
            inv["equipment"][item["type"]].append({"name": item["name"], "rarity": item["rarity"]})
            obtained.append(item)

        await self.update_user(user_id, money, inv)

        lines = [
            f"• {item['name']} ({item['rarity'].capitalize()} {item['type'].capitalize()})"
            for item in obtained
        ]

        embed = discord.Embed(
            title="🎁 Dark Crate Opened",
            description=f"You received **{count}** item(s):\n" + "\n".join(lines),
            color=discord.Color.dark_purple(),
        )
        await interaction.response.send_message(embed=embed)

    # -----------------------------
    # Equipment & Loadout
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

        slot = interaction.namespace.slot.value if hasattr(interaction, "namespace") else None
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

        slot_value = slot.value  # "weapon" or "defense"

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


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))