# Panel internals

What each status looks like and does is in the [recipe](../RECIPE.md). This
page covers how the sprites are built and how to work on the panel.

## Sprites

The [generator](../tools/tibia860.py) draws each outfit pose with all of its
addon layers, not just the base looktype, so the panel character wears the full
outfit (for 130, the hat and the belt potion). It shades the outfit mask with
gold hair (`#FFAA00`), an indigo top (`#3F3FCC`), brown trousers (`#B46337`),
and gray boots (`#737373`). It rotates the frames −45° with bicubic resampling,
crops all 12 poses in each outfit to shared bounds, and scales them onto a
64×64 PNG canvas with Lanczos resampling. Outfits are 64×64 (2×2 tiles) in this
pack; tiles are placed bottom-right first, following the client. The same script
reads the mod's `loot.js` and renders each reward once for the rail into
`sprites/done/` (bottom-right anchored, up to 29×32 px, small items doubled with
nearest sampling), so the mod overlays one shared loot image on the outfit's
done pose instead of storing a sprite per outfit and item.

The panel's scenes are layered the same way, so no image is stored per
combination:

| Layer | Files in `sprites/` | Drawing |
| --- | --- | --- |
| Character | `<outfit>/fight.png` | East-facing standing pose, bottom-left, up to 40×56 px. |
| Monster | `monsters/<looktype>.png` | West-facing, still, bottom-aligned and centered at x=72, up to 48×56 px. |
| Spell | `spells/<missile>-<0–8>.png` | Frames 0–4 fly the 30 px missile from x=34 to the monster; 5–8 sample its hit effect. |
| Cornered character | `<outfit>/cornered.png` | Needs you: south-facing, centered at x=22. |
| Blood | `cornered/pool.png` | Needs you: splatter under the character, up to 44 px wide and flattened. |
| Close monster | `melee/<looktype>.png` | Needs you: the same monster with its left edge at x=29. |
| Burst | `cornered/<sprite id>.png` | Needs you: 40 px, on the character. |
| Corpse | `corpses/<looktype>.png` | Done: centered at x=72, up to 48×48 px. Reuses the Working character. |
| Reward | `rewards/<item>.png` | Done: the loot on the corpse, 22–28 px on its longer side. |
| Zzz | `sleep/<0–6>.png` | Idle: up to 26×28 px, left edge at x=30. Reuses the Working character. |

Scene sizes and positions are constants at the top of
[`tools/tibia860.py`](../tools/tibia860.py); frame timing is in `main.js`.
`SPELL_STEPS` there must match the generator's flight and hit steps, and
`SLEEP_FRAMES` the phases of the sleep effect.

## Changing monsters and spells

In [`fights.js`](../mods/agents-tibia/fights.js), `MONSTERS` lists monsters as
`[looktype, corpse item id]` pairs, and each `SPELLS` entry is a
`[missile id, hit effect id]` pair. A monster's corpse item ID is the
`monster.corpse` value in its server definition (for example, TFS
`data/monsters/`). [`loot.js`](../mods/agents-tibia/loot.js) lists the loot.
After editing either file, regenerate and install, so the panel never names an
image that has not been rendered (see the [README](../README.md)).

## Previewing every status

Herdr treats any program that reports a status (OSC 7501) as an agent, so a
script can show each state without starting a real one. This opens a
`tibia-demo` space with one demo agent per status. Each works for 12 seconds,
so it has a monster, then reports its final state:

```sh
mkdir -p /tmp/tibia-demo
for state in working blocked done idle; do
  hc run --bg --rm --no-parent --no-notify --name "tibia-$state" \
    --cwd /tmp/tibia-demo \
    --label herdr.space=tibiademo --label "herdr.tab=tibiademo-$state" -- \
    sh -c 'report() { printf "\033]7501;state=%s\033\\" "$1"; }
      report working; sleep 12; report "$1"; sleep 3600' demo "$state"
done
```

An `idle` demo shows as Done until you look at it. The demos end after an hour;
`hc kill tibia-working` (and so on for each state) ends them sooner.

## macOS and Linux

- **macOS** The mod clips the 3 px transparent border around each padded PNG to
  hide thin rendering lines along the sprite edges. The rail bob moves the
  clipped sprite as a unit. `tools/tibia860.py` writes `sprites/padded/` for this.
- **Linux** The mod animates the image directly, without the padded copies.

## Herdr upgrades

Start the upgraded app, run `python3 install.py` again, and switch to `tibia`.
`mods/agents-tibia/main.js` is a modified copy of the shipped
`mods/agents/main.js` from Herdr 0.1.18: merge upstream changes into it by hand,
then verify the priority headers, grouped rows, and rail.
