import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import json

SHOP_ITEMS = {
    "apple": 10,
    "sword": 100,
    "shield": 75,
    "potion": 25
}

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------------
    # Helper Functions
    # -----------------------------
    async def get_user(self, user_id):
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

    async def update_user(self, user_id, money, inventory):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute(
                "UPDATE Economy SET money = ?, inventory = ? WHERE user_id = ?",
                (money, json.dumps(inventory), user_id)
            )
            await db.commit()

    # -----------------------------
    # Autocomplete Functions
    # -----------------------------

    async def buy_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for /buy — show all shop items."""
        return [
            app_commands.Choice(name=item, value=item)
            for item in SHOP_ITEMS.keys()
            if current.lower() in item.lower()
        ][:25]

    async def sell_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for /sell — show only items user owns."""
        _, inventory = await self.get_user(interaction.user.id)

        return [
            app_commands.Choice(name=item, value=item)
            for item in inventory.keys()
            if current.lower() in item.lower()
        ][:25]

    # -----------------------------
    # Slash Commands
    # -----------------------------

    @app_commands.command(name="profile", description="View your balance and inventory")
    async def profile(self, interaction: discord.Interaction):
        money, inventory = await self.get_user(interaction.user.id)

        msg = f"**💰 Balance:** ${money}\n\n"
        msg += "**🎒 Inventory:**\n"

        if not inventory:
            msg += "You have no items."
        else:
            for item, qty in inventory.items():
                msg += f"- **{item}** × {qty}\n"

        await interaction.response.send_message(msg)

    @app_commands.command(name="shop", description="View the shop items")
    async def shop(self, interaction: discord.Interaction):
        msg = "**🛒 Shop Items:**\n"
        for item, price in SHOP_ITEMS.items():
            msg += f"- **{item}** — ${price}\n"
        await interaction.response.send_message(msg)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(
        item="The item you want to buy",
        quantity="How many you want to buy"
    )
    @app_commands.autocomplete(item=buy_autocomplete)
    async def buy(self, interaction: discord.Interaction, item: str, quantity: int = 1):
        item = item.lower()

        if item not in SHOP_ITEMS:
            return await interaction.response.send_message("That item doesn't exist.", ephemeral=True)

        if quantity < 1:
            return await interaction.response.send_message("Quantity must be at least 1.", ephemeral=True)

        price = SHOP_ITEMS[item] * quantity
        money, inventory = await self.get_user(interaction.user.id)

        if money < price:
            return await interaction.response.send_message("You don't have enough money.", ephemeral=True)

        money -= price
        inventory[item] = inventory.get(item, 0) + quantity

        await self.update_user(interaction.user.id, money, inventory)
        await interaction.response.send_message(
            f"You bought **{quantity}× {item}** for ${price}!"
        )

    @app_commands.command(name="sell", description="Sell an item from your inventory")
    @app_commands.describe(
        item="The item you want to sell",
        quantity="How many you want to sell"
    )
    @app_commands.autocomplete(item=sell_autocomplete)
    async def sell(self, interaction: discord.Interaction, item: str, quantity: int = 1):
        item = item.lower()

        if item not in SHOP_ITEMS:
            return await interaction.response.send_message("That item doesn't exist.", ephemeral=True)

        money, inventory = await self.get_user(interaction.user.id)

        if item not in inventory:
            return await interaction.response.send_message("You don't own that item.", ephemeral=True)

        if quantity < 1:
            return await interaction.response.send_message("Quantity must be at least 1.", ephemeral=True)

        if inventory[item] < quantity:
            return await interaction.response.send_message("You don't have that many.", ephemeral=True)

        sell_price = (SHOP_ITEMS[item] // 2) * quantity

        inventory[item] -= quantity
        if inventory[item] <= 0:
            del inventory[item]

        money += sell_price

        await self.update_user(interaction.user.id, money, inventory)
        await interaction.response.send_message(
            f"You sold **{quantity}× {item}** for ${sell_price}!"
        )


async def setup(bot):
    await bot.add_cog(Economy(bot))