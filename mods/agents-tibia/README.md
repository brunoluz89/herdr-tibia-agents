# agents-tibia

Herdr's Agents panel with an animated Tibia scene for each agent status. The
`tibia` layout uses this mod, a modified copy of the shipped `agents` mod from
Herdr 0.1.18.

Click the character in the panel header to choose among the outfits, male or
female. The choice is kept in the Herdr shared setting `tibia.outfit` (a
looktype). Missing or unknown values use 130.

`outfits.js`, `loot.js`, and `fights.js` list the outfits, loot, monsters, and
spells. After editing them, regenerate the sprites with `tools/tibia860.py` from
the source repository and run its `install.py`.
