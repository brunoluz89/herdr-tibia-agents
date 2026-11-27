# agents-tibia

Herdr's Agents panel with an animated Tibia scene for each agent status. The
`tibia` layout uses this mod, a modified copy of the shipped `agents` mod from
Herdr 0.1.18.

Every agent wears its own outfit: one picked for it by hand (shared
`tibia.agentOutfits`), else the first free one of the agent order (shared
`tibia.agentOrder`, else `AGENT_OUTFITS`). Click an agent's character to open
the `tibia-picker` dialog, where you pick its outfit, set each outfit's colors
and vocation, and set the order.

Vocations change the Working scene: sorcerers and druids cast their own spells,
paladins shoot a random missile each shot and leave blood on the monster, and
knights walk up and strike it. Each outfit has its own (shared
`tibia.outfitVocations`, by looktype); an agent whose outfit has none casts the
mixed spells of before.

`outfits.js`, `loot.js`, and `fights.js` list the outfits, loot, monsters, and
attacks. After editing
them, regenerate the sprites with `tools/tibia860.py` from the source
repository and run its `install.py`.
