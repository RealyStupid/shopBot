import aiosqlite

async def init_economy_db():
    async with aiosqlite.connect("economy.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS Economy (
                user_id INTEGER PRIMARY KEY,
                money INTEGER,
                inventory TEXT
            )
        """)
        await db.commit()