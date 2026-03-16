# 🐉 Boss Creation Guide (For Contributors)

This document explains how to create a new boss for **Yura**, the ShopBot project.  
Bosses are modular, theme‑driven, and designed to integrate seamlessly into the turn‑based combat system.

Follow this guide to ensure your boss is balanced, cinematic, and fully compatible with the existing architecture.

------------------------------------------------------------
1️⃣ STEP 1 — DEFINE THE BOSS CONCEPT
------------------------------------------------------------

Before writing any code, decide the boss’s identity.

Think about:
- Theme (fire, ice, undead, cosmic, mechanical, etc.)
- Personality (brutal, cunning, ancient, chaotic)
- Combat style (burst damage, tanky, multi‑hit, status effects)
- Threat level (1–4)

Example concept:
```
Frost Wyrm: Ice dragon, cold and calculating, high burst damage, Threat 3
```
A clear concept ensures your boss feels intentional and consistent.

------------------------------------------------------------
2️⃣ STEP 2 — ASSIGN CORE STATS
------------------------------------------------------------

Each boss requires four core stats:

- hp: total health
- damage: (min, max) damage per attack
- reward: money given to all surviving players
- bonus: extra money for the killing blow

Threat level guidelines:
- Threat 1 → low HP, low damage
- Threat 2 → moderate HP/damage
- Threat 3 → high HP/damage
- Threat 4 → very high HP/damage

Example stats:
```Python
{
    "name": "Frost Wyrm",
    "threat": 3,
    "hp": 420,
    "damage": (28, 45),
    "reward": 950,
    "bonus": 150
}
```

------------------------------------------------------------
3️⃣ STEP 3 — ADD THE BOSS TO THE BOSSES LIST
------------------------------------------------------------

In the bossfight system, add your boss entry to the BOSSES list.

Example:
```Python
BOSSES.append({
    "name": "Frost Wyrm",
    "threat": 3,
    "hp": 420,
    "damage": (28, 45),
    "reward": 950,
    "bonus": 150
})
```

This makes the boss availabel for possible fights during /bossfight.

------------------------------------------------------------
4️⃣ STEP 4 — ADD BOSS FLAVOR TEXT
------------------------------------------------------------

Flavor text gives your boss personality and makes combat cinematic.

Add 3–5 unique attack lines to the FLAVOR_TEXT dictionary.

Example:
```Python
FLAVOR_TEXT["Frost Wyrm"] = [
    "The Frost Wyrm exhales a chilling blizzard at {player}, freezing them for **{dmg}** damage!",
    "The Frost Wyrm lashes its icy tail at {player}, striking for **{dmg}** damage!",
    "The Frost Wyrm screeches, unleashing shards of ice at {player} for **{dmg}** damage!"
]
```

Guidelines:
- Use {player} and {dmg} placeholders
- Keep lines short and dramatic
- Match the boss’s theme
- Avoid repeating verbs too often

The system will automatically:
- Mix these with generic lines
- Use critical hit lines when damage is high

------------------------------------------------------------
5️⃣ STEP 5 — OPTIONAL: ADD SPECIAL MECHANICS
------------------------------------------------------------

If your boss needs unique behavior, add it inside the `boss_turn()` logic.

Possible mechanics:
- Freeze (skip next player turn)
- Burn (damage over time)
- Multi‑hit attacks
- Enrage at 50% HP
- Shields or damage reduction

Document any special mechanics you add.

------------------------------------------------------------
6️⃣ STEP 6 — PLAYTEST & BALANCE
------------------------------------------------------------

Run /bossfight and test your boss in both solo and multiplayer.

Check:
- Does the boss feel too weak or too strong?
- Does the damage range match the threat level?
- Does the flavor text feel right?
- Are the rewards fair?

Adjust stats until the boss feels balanced.

------------------------------------------------------------
7️⃣ STEP 7 — DOCUMENT THE BOSS
------------------------------------------------------------

Add an entry to the boss index so contributors can track what exists.

Example:
```
Boss: Frost Wyrm
Threat: 3
HP: 420
Damage: 28–45
Reward: 950
Bonus: 150
Theme: Ice
Personality: Cold, calculating
Flavor: Added
Special Mechanics: None
```

------------------------------------------------------------
🎉 YOU’RE DONE!
------------------------------------------------------------

Following this guide ensures your boss:
- Fits the system
- Feels unique and thematic
- Is balanced and fair
- Uses flavor text correctly
- Works in both solo and multiplayer
- Requires no extra code changes

Thank you for contributing to Yura!