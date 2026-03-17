import discord
from discord.ext import commands
from discord import app_commands

class NewUsers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="quickstart", description="Learn how to play the game and use the bot's RPG features.")
    async def quickstart(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📘 Quickstart Guide",
            description="Welcome to the adventure! Here’s everything you need to know to begin.",
            color=discord.Color.dark_purple()
        )

        # SECTION 1 — Your Profile
        embed.add_field(
            name="👤 Your Profile",
            value=(
                "**/profile** — View your stats, money, equipment, and consumables.\n"
                "**/loadout** — See what gear you currently have equipped.\n"
                "**/equipment** — View all weapons and armor you own."
            ),
            inline=False
        )

        # SECTION 2 — Earning Money
        embed.add_field(
            name="💰 Earning Money",
            value=(
                "**Quests:** Random events appear in the quest channel. Be the first to type the trigger word!\n"
                "**Bossfights:** Team up with others to defeat powerful bosses.\n"
                "**Crates:** Earn rare gear by opening crates.\n"
            ),
            inline=False
        )

        # SECTION 3 — Shopping & Items
        embed.add_field(
            name="🛒 Shopping",
            value=(
                "**/shop** — View items for sale.\n"
                "**/buy** — Purchase weapons, armor, consumables, or crates.\n"
                "**Consumables:**\n"
                "• 🍎 Apple — Heal 20 HP in battle.\n"
                "• 🧪 Potion — Permanently increase max HP by 20."
            ),
            inline=False
        )

        # SECTION 4 — Equipment
        embed.add_field(
            name="⚔️ Equipment & Gear",
            value=(
                "**/equip** — Equip a weapon or defensive item.\n"
                "**/unequip** — Remove equipped gear.\n\n"
                "**Rarity Bonuses:**\n"
                "• Common: +10\n"
                "• Uncommon: +30\n"
                "• Rare: +70\n"
                "• Legendary: +120\n"
                "• Godlike: +200\n\n"
                "Weapons increase **damage**.\n"
                "Shields/Armor increase **defense**."
            ),
            inline=False
        )

        # SECTION 5 — Bossfights
        embed.add_field(
            name="💀 Bossfights",
            value=(
                "**/bossfight** — Start a server-wide boss battle.\n"
                "Type **join** to enter.\n\n"
                "**Battle Commands:**\n"
                "• `attack` — Deal damage.\n"
                "• `protect` — Reduce incoming damage.\n"
                "• `apple` — Heal 20 HP.\n"
                "• `potion` — Increase max HP by 20.\n"
                "• `run` — Leave the fight.\n\n"
                "Bosses drop **money** and bonus rewards."
            ),
            inline=False
        )

        # SECTION 6 — Crates
        embed.add_field(
            name="🎁 Crates",
            value=(
                "**/opencrate** — Open a Dark Crate.\n"
                "Crates contain **2–3 Rare+ items**.\n"
                "Higher rarity = stronger bonuses."
            ),
            inline=False
        )

        # SECTION 7 — Tips
        embed.add_field(
            name="✨ Tips for New Players",
            value=(
                "• Equip your best weapon before bossfights.\n"
                "• Potions permanently increase max HP — use them wisely.\n"
                "• Protect reduces damage and stacks with armor.\n"
                "• Crates are the best way to get high-rarity gear.\n"
                "• Quests are fast money — keep an eye on the quest channel."
            ),
            inline=False
        )

        embed.set_footer(text="Good luck, adventurer. Your journey begins now.")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(NewUsers(bot))