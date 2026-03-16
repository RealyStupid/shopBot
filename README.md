# 🛍️ Yura: A Feature‑Rich Economy Bot for Discord
(Repository name: ShopBot)

Yura is a modular Discord bot focused on delivering a fun, expandable **economy experience** for servers.  
Players can earn money, buy items, complete quests, and interact with a persistent inventory system.

Over time, Yura has grown beyond a simple shop bot — now featuring a full RPG‑style **boss fight system** that integrates directly with the economy and inventory.

This README explains Yura’s features, structure, and how contributors can help expand the project.

------------------------------------------------------------
🚀 FEATURES
------------------------------------------------------------

💰 Economy System  
- Persistent currency stored in SQLite  
- Inventory system with consumables & equipment  
- Shop-ready architecture  
- Easy to expand with new items  

🎒 Inventory System  
- Apples, potions, swords, shields, and more  
- Items directly affect combat  
- Permanent stat upgrades via potions  

🧩 Quest System  
- Daily quests  
- Repeatable tasks  
- Rewards tied into the economy  
- Expandable quest definitions  

💀 Boss Fight System (Optional RPG Feature)  
Although Yura is primarily an economy bot, it includes a fully‑featured RPG boss system:

- /bossfight command  
- Join window with countdown  
- Solo & multiplayer support  
- Turn‑based combat  
- Player stat panel every turn  
- Inventory-integrated actions  
- Boss AI with damage calculation  
- Cinematic flavor text for both players and bosses  
- Rewards + killing blow bonus  

This system is modular and can be expanded with new bosses, items, and mechanics.

------------------------------------------------------------
🧠 HOW THE BOSS FIGHT SYSTEM WORKS
------------------------------------------------------------

🔹 Start a fight  
Use /bossfight to spawn a random boss.

🔹 Join the battle  
Players type "join" during the join window.

🔹 Turn-based combat  
Each player receives a stat panel showing HP, items, and status.

Players choose an action:
- attack  
- protect  
- apple  
- potion  
- run  

🔹 Boss AI  
Bosses attack using:
- Randomized damage  
- Damage reduction from player actions  
- Boss-specific flavor text  

🔹 Rewards  
Survivors earn money.  
The killing blow earns a bonus.

------------------------------------------------------------
🧱 PROJECT STRUCTURE
------------------------------------------------------------
```
cogs/
│
├── bossfight.py   (Boss fight engine)
├── economy.py     (Currency + inventory)
├── quests.py      (Quest system)
│
main.py            (Bot entry point)
economy.db         (SQLite database)
```
------------------------------------------------------------
🧩 CONTRIBUTING
------------------------------------------------------------

Contributions are welcome!  
Here are the main areas where collaborators can help:

✔ Add new items  
✔ Add new quests  
✔ Add new bosses  
✔ Improve flavor text  
✔ Add new mechanics  

------------------------------------------------------------
🐉 BOSS CREATION GUIDE (FOR CONTRIBUTORS)
------------------------------------------------------------

1️⃣ DEFINE THE BOSS CONCEPT  
Think about:
- Theme  
- Personality  
- Combat style  
- Threat level (1–4)

Example:
```
Frost Wyrm: Ice dragon, cold and calculating, high burst damage, Threat 3
```

the full guide can be found in `BOSS_CREATION.md`

------------------------------------------------------------

6️⃣ PLAYTEST & BALANCE  
Run /bossfight and adjust:
- HP  
- Damage  
- Rewards  
- Flavor text  

------------------------------------------------------------

7️⃣ DOCUMENT THE BOSS  
Add an entry to the boss index:

{REPLACE_WITH_BOSS_DOCUMENTATION}

------------------------------------------------------------
🛠️ SETUP & INSTALLATION
------------------------------------------------------------

Requirements:
- Python 3.10+  
- discord.py  
- aiosqlite  

- Run the bot:
```
py main.py
```

------------------------------------------------------------
📜 LICENSE
------------------------------------------------------------

This project is protected under the RealyStupid Proprietary License (RPL‑1.0).  
See the LICENSE file for details.

------------------------------------------------------------
🤝 CREDITS
------------------------------------------------------------

Created by RealyStupid  
Bot name: Yura  
Repository name: ShopBot  
Contributions welcome!
