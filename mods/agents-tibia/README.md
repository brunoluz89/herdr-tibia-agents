# agents-tibia

Herdr's Agents panel with an animated Tibia scene for each agent status. The
`tibia` layout uses this mod, a modified copy of the shipped `agents` mod from
Herdr 0.1.18.

Every agent wears its own outfit: one picked for it by hand (shared
`tibia.agentOutfits`), else the first free one of the agent order (shared
`tibia.agentOrder`, else `AGENT_OUTFITS`). Click an agent's character to open
the `tibia-picker` dialog, where you pick its outfit, recolor outfits and set
the order.

`outfits.js`, `loot.js`, and `fights.js` list the outfits, loot, monsters, and
spells. After editing
them, regenerate the sprites with `tools/tibia860.py` from the source
repository and run its `install.py`.
