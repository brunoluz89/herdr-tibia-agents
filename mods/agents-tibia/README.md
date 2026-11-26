# agents-tibia

Herdr's Agents panel with an animated Tibia scene for each agent status. The
`tibia` layout uses this mod, a modified copy of the shipped `agents` mod from
Herdr 0.1.18.

Set the Herdr shared setting `tibia.outfit` to choose the character: 128–134,
136–142, or 144. Missing or unknown values use 130.

`loot.js` and `fights.js` list the loot, monsters, and spells. After editing
them, regenerate the sprites with `tools/tibia860.py` from the source
repository and run its `install.py`.
