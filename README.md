# Tibia Agents for Herdr

Herdr's Agents panel, with an animated Tibia scene for each agent status.

![Tibia Agents](preview.png)

Every agent gets its own character, in an order you choose. Click an agent's
character to give it another outfit (24 outfits and 7 retro ones, male or
female) and to recolor that outfit.

| Status | Scene |
| --- | --- |
| Needs you | The monster closes in; blood on the character and the floor. |
| Done | The monster's corpse with a piece of loot on it, also when you watched the agent finish. |
| Working | The character walks, casting a spell at a monster that walks away. |
| Idle | The character dozes, until the agent finishes its first job. |

The art is CipSoft's, taken from Tibia client files. Keep this repository
private, or remove `mods/agents-tibia/sprites/` **and its Git history** before
publishing it.

## Install or update

Needs Herdr (built against 0.1.18), started at least once, and `python3`. The
sprites are included. From this directory:

```sh
python3 install.py
herdr-app do layout.switch '{"name":"tibia"}'
```

The installer checks the mods, copies them to
`~/.config/herdr-app/mods/agents-tibia/` and `mods/tibia-picker/`, and writes
`layouts/tibia.json` from your shipped `main` layout. It saves any mod and layout it replaces under
`~/.config/herdr-app/backups/`. Run it again after pulling changes or after a
Herdr upgrade.

`layouts/tibia.json` is rebuilt each time, so reapply any changes you made to
it. For another Herdr home, pass `--home`.

To go back: `herdr-app do layout.switch '{"name":"main"}'`.

## Customize

- **Characters:** each new agent or sub-agent takes the first outfit of the
  agent order that no live agent wears; past the end of the order, outfits
  repeat. The default order is Citizen, Mage, Summoner, Warrior, Hunter, Noble,
  Knight (male).
- **Outfit picker:** click an agent's scene (grouped view), or the small
  character that shows beside the pin when you hover a row. The dialog has two
  tabs:
  - *Outfit:* pick an outfit, male or female, then recolor it: head, top,
    trousers and boots, from Tibia's 133-color palette, with a live preview.
    **Salvar cores** (save colors) recolors that outfit for every agent
    wearing it; **Vestir este agente** (dress this agent) also gives the outfit
    to that agent. **Automático** hands the agent back to the order.
  - *Ordem dos agentes* (agent order): any outfits, as many as you like, in
    the order agents get them.

  The command palette has "Tibia: outfits e cores" (the dialog without an
  agent) and "Tibia: todos os agentes no automático". Recoloring needs the
  client files below: the picker runs `tools/recolor.py`.
- **Wording:** the picker's labels are in Portuguese.
- **Outfits, monsters, spells, loot:** edit `outfits.js`, `fights.js`, or
  `loot.js` in `mods/agents-tibia/`, regenerate the sprites, and run the
  installer.

See [panel internals](docs/panel.md) for the sprite layers, previewing every
status with demo agents, platform notes, and Herdr upgrades.

## Regenerate the sprites

Needs Pillow, plus `Tibia.spr` and `Tibia.dat` of the extended 8.6 profile
(`cip860-extended`, from release `15.25.0a00a0` of
[tibia-client](https://github.com/dudantas/tibia-client/releases/latest)) in
`~/Documents/tibia-8.6/`:

```sh
python3 tools/dump-dat-860.py     # once per client version
python3 tools/tibia860.py         # writes mods/agents-tibia/sprites/
python3 install.py
```

For client files kept elsewhere, pass `--dat <path>/Tibia.dat` to the dump and
`--source <path>` to the generator. The generator also writes a contact sheet,
`preview-860.png`, and `frames/`, each outfit's uncolored frames, beside the
client files. The picker recolors from `frames/` (about a second per preview)
and keeps the chosen colors in `cores.json` there, which the generator reads
too. Without `cores.json`, every outfit gets the classic colors.

When changing the animations, keep `SPELL_STEPS`, `SLEEP_FRAMES` and
`WALK_STEPS` in `main.js` equal to the number of frames the generator writes.
