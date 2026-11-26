# Tibia Agents

Herdr's left sidebar Agents panel, where every agent status is a small Tibia
scene: a mage fighting a monster while the agent works, cornered when it needs
you, standing over the loot when it is done, and dozing when it is idle.

![Tibia Agents](preview.png)

## What you see

The `tibia` layout is the shipped `main` layout with only the Agents block
replaced by this mod. Colors and type come from the active theme.

- **Header** (41 px): "Agents" at 11.5 px, dim, and a 14 px sort icon.
- **Priority view:** sections in the order Needs you, Done, Working, Idle, after
  Pinned when something is pinned. A section header is 76 px high: the agent
  count (dim), the section name in its status color, then one 96×64 scene. Rows
  below are 30 px: program icon, space name, dimmed detail, machine name for a
  remote agent, and time since the last change (`<1m`, `5m`, `2h`, `3d`).
- **Grouped by space:** space headers (34 px); agent rows 70 px high with their
  own 96×64 scene at the right; sub-agents as a tree beneath their parent.
- **Rail** (sidebar narrower than 160 px; 44 px, 76 on macOS): 26 px rows with
  the agent number and a 20×20 sprite, and a `»` button at the bottom.

## How it behaves

| Status | Panel (96×64) | Rail (20×20) |
| --- | --- | --- |
| Working | The mage stands bottom-left facing east and casts at a monster bottom-right, facing west. A missile flies in 5 frames, its hit effect shows in 4, 120 ms each, then 600 ms pause. | Mage in its walking frame, bobbing 1 px every 240 ms. |
| Needs you (blocked) | The mage faces south on a blood splatter, the monster right beside. A blood burst plays on the mage: 6 frames, 85 ms each, then 320 ms pause. | Mage with the burst. |
| Done | Still: the mage as in Working, the monster's corpse where it stood, one loot item on the corpse. | Mage beside the item. |
| Idle | The mage as in Working with Zzz beside its head: 7 frames, 220 ms each, then 660 ms pause. | Mage facing south, still. |

- The monster is picked when an agent starts working and stays through Needs you
  and Done. The spell is picked per working stretch, the loot per completion.
  Picks are random, independent, and stable across redraws; a panel reload picks
  anew.
- 8 monsters (dragon, demon, cyclops, orc, giant spider, hydra, rotworm,
  skeleton), 8 spells (ice, holy burst, fire, energy, energy ball, sudden death,
  earth, small holy), and 10 loot items (gold coins, violet gem, health potion,
  banana, fire sword, golden helmet, mastermind shield, backpack of holding,
  frozen starlight, thunder hammer).
- Agents showing the same status animate in step. Burst, spell, and sleep
  animations stop when not drawn or when the window is hidden.
- A priority header shows the scene of the first agent listed in its section
  with that status, so priority rows have no scenes of their own.
- Click a row to focus its pane; click a sub-agent without a pane to peek at it.
- Hover a row to get a pin button; pinned agents come first.
- Click a header to fold its group. A row's chevron, or its program icon, folds
  its sub-agents.
- The sort icon opens a 200×140 popup: Priority or Grouped by space.
- A sub-agent without a pane counts `error` as blocked and `done` as idle.

## Built from

- One mod, `agents-tibia` (`main.js`, `loot.js`, `fights.js`, `sprites/`), a
  modified copy of the shipped `agents` mod of Herdr 0.1.18. Its `mod.json` has
  `"place": "none"`. The layout puts it in the block with id `agents`.
- Props: `{ sortMenu: true }` renders the sort popup; no props renders the panel.
- `herdr` functions: `agents`, `terminals`, `panes`, `focused`, `spaces`, `run`,
  `theme`, `shared`, `setShared`, `setAgentOrder`, `openOverlay`,
  `closeOverlay`, `props`, `window`, `layout`.
- Commands: `pane.focus`, `terminal.peek`, `terminal.pin`, `layout.resize`.
- State: shared `tibia.outfit`, `agents.sort`, `sidebar.width`,
  `sidebar.collapsed`; `localStorage` `changed` (each agent's state, time, and
  fight) and `pins`.
- Icons come from the shipped `workspace-chrome` mod.
- Reaches no network, runs no programs, and reads no files outside Herdr's mods.
  `install.py` and `tools/` run outside Herdr; the installer runs
  `herdr-app check`.
- Art: PNGs made by `tools/tibia860.py` from the extended Tibia 8.6 client. Each
  scene is a stack of full-size transparent layers: character
  (`<outfit>/fight.png` or `<outfit>/cornered.png`), then `monsters/` and
  `spells/`, or `cornered/` and `melee/`, or `corpses/` and `rewards/`, or
  `sleep/`.
- Outfits are shaded gold hair `#FFAA00`, indigo top `#3F3FCC`, brown trousers
  `#B46337`, gray boots `#737373`, with every addon layer.

## Watch out

- The extended pack's outfit and monster sprites are stored rotated 45°; rotate
  them -45°. Sprite 0 of a frame is its bottom-right tile.
- Looktype 160 has no art in this pack.
- On macOS, images show thin edge lines. Draw the copies in `sprites/padded/`
  (3 px transparent border) clipped to size.
- Animate with one timer per animation that calls `notify`, and ask for a frame
  only when drawing it, so unused timers stop.
- Right after a reload, images can be blank until they load.
- `SPELL_STEPS` and `SLEEP_FRAMES` in `main.js` must match the frames on disk.
- `install.py` expects the shipped `main` layout to have exactly one block with
  id `agents` showing the `agents` mod, and stops otherwise. Upstream changes to
  the shipped mod need merging into `main.js` by hand.
- The macOS rendering of the 96×64 scenes has not been verified.

## Done when

- `herdr-app check mods/agents-tibia` passes.
- `python3 install.py` writes the mod and `layouts/tibia.json`, and
  `herdr-app status` shows no errors after switching to `tibia`.
- Agents reporting `working`, `blocked`, `done`, and `idle` (OSC 7501) show
  their four scenes in priority headers and in grouped rows.
- An agent going from working to blocked or done keeps its monster.
- The rail shows the 20 px sprites.
