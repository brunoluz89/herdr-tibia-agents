#!/usr/bin/env python3
"""Build the local Herdr status sprites from the extended 8.6 client assets.

Reads the cip860-extended Tibia.dat/Tibia.spr pair: 32-bit sprite ids, no
frame-group splitting, outfits up to 2x2 tiles. Tile placement follows the
client convention (sprite 0 is the bottom-right tile), outfit colors keep the
classic palette, and each outfit pose is composed with all of its addon layers.
"""

import argparse
import json
import re
from pathlib import Path
from struct import unpack_from

from PIL import Image, ImageDraw

ATTACK_EFFECT = 1
PREVIEW_LOOT = (3036, 3280, 3365)  # The preview sheet's samples.
ITEM_FRAMES = {3031: (3, 1)}  # Gold coins: the fullest pile, as if 100+ were dropped.
PALETTE = {
    (255, 255, 0): (255, 170, 0),
    (255, 0, 0): (63, 63, 204),
    (0, 255, 0): (180, 99, 55),
    (0, 0, 255): (115, 115, 115),
}
# The mask color of each part, by the names the color page (cores-dos-outfits.html) writes.
PARTS = {"cabeca": (255, 255, 0), "corpo": (255, 0, 0), "pernas": (0, 255, 0), "pes": (0, 0, 255)}
# Walking steps per character and monster; main.js's WALK_STEPS must match.
WALK_STEPS = 2
# The images each outfit gets in sprites/<looktype>/.
OUTFIT_LABELS = ("idle", "working", "working-2", "fight", *(f"walk-{step}" for step in range(WALK_STEPS)),
                 "step1", "step2", "cornered", "need_help", "done")
TILE = 32
CANVAS = 64
SCALE = CANVAS / 48  # The layout budgets below were tuned on a 48 px canvas.
EDGE_PADDING = 3  # Matched by the macOS sprite renderer in agents-tibia/main.js.
SOUTH = 2
EAST = 1
WEST = 3
# The panel scenes share one wide canvas. Working: the character bottom-left
# shoots at a monster bottom-right, or, as a knight, walks up and strikes it.
# Needs you: the monster has closed in. Done: the loot lies on the monster's
# corpse. Idle: the character dozes.
FIGHT_WIDTH = 96
MONSTER_CENTER = 72
MISSILE_START = 34
SPELL_HEIGHT = 34  # y of the missile path and of the hit effect.
MISSILE_SIZE = 30
EFFECT_TILE = 34
FLIGHT_STEPS = 5
# Missiles whose art sits low in its tile, centered on the flight path instead.
LOW_MISSILES = (1, 17, 18, 21, 28)  # The spears.
HIT_STEPS = (0.2, 0.4, 0.6, 0.8)  # Points of the hit effect shown; main.js counts all steps.
STEP_MARGIN = 6  # Room left of a knight's walking frame (step1, step2); main.js shifts it back.
CORNERED_CENTER = 22  # x of the cornered character, its blood and its burst.
MELEE_LEFT = 29  # Left edge of the monster beside the cornered character.
POOL_ITEM = 2889  # The splatter shape of a fluid on the floor.
BLOOD = (2, 0)  # Its dat pattern for blood.
POOL_SIZE = 44
BURST_SIZE = 40
BLOOD_SIZE = 42  # The blood spurting from a monster hit by a knight or paladin.
REWARD_SIZES = (22, 28)  # Smallest and largest loot on a corpse, by its longer side.
SLEEP_EFFECT = 33  # The Zzz of a sleeping character.
SLEEP_SIZE = (26, 28)  # Room for the Zzz, beside the character's head.
SLEEP_LEFT = 30  # Left edge of the Zzz.


class SpriteArchive:
    def __init__(self, path):
        self.data = path.read_bytes()
        signature, self.count = unpack_from("<II", self.data)
        self.table_end = 8 + self.count * 4
        if signature != 0x4C220594 or self.table_end > len(self.data):
            raise ValueError("Expected the extended 8.6 Tibia.spr file")
        self.table = unpack_from(f"<{self.count}I", self.data, 8)

    def pixels(self, sprite_id):
        pixels = bytearray(TILE * TILE * 4)
        if not sprite_id:
            return pixels
        offset = self.table[sprite_id - 1]
        if not offset:
            return pixels
        cursor = offset + 5
        end = cursor + unpack_from("<H", self.data, offset + 3)[0]
        if end > len(self.data):
            raise ValueError(f"Sprite {sprite_id} is truncated")
        data = self.data
        pixel = 0
        while cursor < end:
            skip, solid = unpack_from("<HH", data, cursor)
            cursor += 4
            pixel += skip
            if pixel + solid > TILE * TILE or cursor + solid * 3 > end:
                raise ValueError(f"Invalid run in sprite {sprite_id}")
            for _ in range(solid):
                dest = pixel << 2
                pixels[dest:dest + 3] = data[cursor:cursor + 3]
                pixels[dest + 3] = 255
                cursor += 3
                pixel += 1
        return pixels

    def sprite(self, sprite_id):
        return Image.frombytes("RGBA", (TILE, TILE), bytes(self.pixels(sprite_id)))


class DatIndex:
    def __init__(self, path):
        self.data = json.loads(path.read_text())

    def group(self, category, thing_id):
        try:
            return self.data[category][str(thing_id)]
        except KeyError:
            raise ValueError(f"{category} {thing_id} is missing from the dat index") from None


def sprite_index(group, phase, x, y, z, layer, row, col):
    return group["sprites"][
        ((((((phase * group["patternZ"] + z) * group["patternY"] + y)
            * group["patternX"] + x) * group["layers"] + layer)
          * group["height"] + row) * group["width"] + col)
    ]


def frame(archive, group, phase=0, x=SOUTH, y=0, z=0, layer=0):
    """Compose one frame; dat tile 0 is the bottom-right tile."""
    width, height = group["width"], group["height"]
    image = Image.new("RGBA", (width * TILE, height * TILE))
    for row in range(height):
        for col in range(width):
            sprite_id = sprite_index(group, phase, x, y, z, layer, row, col)
            image.alpha_composite(archive.sprite(sprite_id), ((width - 1 - col) * TILE, (height - 1 - row) * TILE))
    return image


def parse_palette(colors, base):
    palette = dict(base)
    for part, value in colors.items():
        if part not in PARTS or not re.fullmatch(r"#[0-9a-fA-F]{6}", str(value)):
            raise ValueError(f"Invalid color {part!r}: {value!r}")
        palette[PARTS[part]] = tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    return palette


def load_colors(path, looktypes):
    """Palettes from the color page's JSON: {"todos": {...}, "outfits": {"<looktype>": {...}}}."""
    if not path.is_file():
        return PALETTE, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    default = parse_palette(data.get("todos", {}), PALETTE)
    outfits = {}
    for outfit, colors in data.get("outfits", {}).items():
        if not str(outfit).isdigit() or int(outfit) not in looktypes:
            raise ValueError(f"Unknown outfit {outfit!r} in {path}")
        outfits[int(outfit)] = parse_palette(colors, default)
    return default, outfits


def walk_phase(group, step):
    """The animation phase of a walking step: phase 0 stands, the rest walk."""
    return 1 + step % (group["phases"] - 1) if group["phases"] > 1 else 0


def shared_crop(images, box):
    """Crops images to their common bounds and scales them alike to fit `box`, so they don't jitter."""
    boxes = [image.getbbox() for image in images if image.getbbox()]
    bounds = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    scale = min(box[0] / width, box[1] / height, 1)
    size = max(1, round(width * scale)), max(1, round(height * scale))
    return [image.crop(bounds).resize(size, Image.Resampling.LANCZOS) for image in images]


def colorize(base, mask, palette=PALETTE):
    colored = base.copy()
    for y in range(base.height):
        for x in range(base.width):
            red, green, blue, alpha = mask.getpixel((x, y))
            color = palette.get((red, green, blue))
            if alpha and color:
                r, g, b, opacity = base.getpixel((x, y))
                shade = (r * 30 + g * 59 + b * 11) // 100
                colored.putpixel((x, y), (*(shade * channel // 256 for channel in color), opacity))
    return colored


def archive_frames(archive, group):
    """An outfit's uncolored frames, read from the client: (phase, direction, addon, layer) -> image."""
    return lambda phase, direction, addon, layer: frame(archive, group, phase, direction, addon, 0, layer)


def outfit_pose(frames, group, phase, direction, palette):
    """One colorized pose: the base outfit plus every addon layer over it."""
    image = None
    for addon in range(group["patternY"]):
        layer = colorize(frames(phase, direction, addon, 0), frames(phase, direction, addon, 1), palette)
        if image is None:
            image = layer
        else:
            image.alpha_composite(layer)
    return image


def rotated_frame(frames, group, phase, direction, palette):
    return outfit_pose(frames, group, phase, direction, palette).rotate(
        -45, resample=Image.Resampling.BICUBIC, expand=True)


# What tools/recolor.py rebuilds from: each outfit's uncolored frames, kept beside the client.
FRAME_KEYS = ("phases", "patternX", "patternY")


def save_frame_cache(cache, outfit_id, frames, group):
    folder = cache / str(outfit_id)
    folder.mkdir(parents=True, exist_ok=True)
    for phase in range(group["phases"]):
        for direction in range(group["patternX"]):
            for addon in range(group["patternY"]):
                for layer in (0, 1):
                    frames(phase, direction, addon, layer).save(folder / f"{phase}-{direction}-{addon}-{layer}.png")
    (folder / "group.json").write_text(json.dumps({key: group[key] for key in FRAME_KEYS}), encoding="utf-8")


def status_images(frames, group, palette):
    poses = {(phase, direction): rotated_frame(frames, group, phase, direction, palette)
             for phase in range(group["phases"]) for direction in range(group["patternX"])}
    boxes = [sprite.getbbox() for sprite in poses.values() if sprite.getbbox()]
    bounds = (min(box[0] for box in boxes), min(box[1] for box in boxes),
              max(box[2] for box in boxes), max(box[3] for box in boxes))
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    scale = (CANVAS - 1) / max(width, height)
    dimensions = round(width * scale), round(height * scale)

    def place_pose(phase, direction):
        sprite = poses[phase, direction].crop(bounds).resize(dimensions, Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (CANVAS, CANVAS))
        canvas.alpha_composite(sprite, ((CANVAS - sprite.width) // 2, CANVAS - sprite.height))
        return canvas

    standing = place_pose(0, SOUTH)
    images = {"idle": standing, "working": place_pose(1, EAST), "need_help": standing}
    facing_reward = place_pose(0, EAST)
    character = facing_reward.crop(facing_reward.getbbox())
    character.thumbnail((round(33 * SCALE), round(44 * SCALE)), Image.Resampling.LANCZOS)
    done = Image.new("RGBA", (CANVAS, CANVAS))
    done.alpha_composite(character, (0, CANVAS - character.height))
    images["done"] = done
    # Cropped here, since the fight scenes have their own size budget.
    caster = facing_reward.crop(facing_reward.getbbox())
    caster.thumbnail((40, 56), Image.Resampling.LANCZOS)
    fight = Image.new("RGBA", (FIGHT_WIDTH, CANVAS))
    fight.alpha_composite(caster, (0, CANVAS - caster.height))
    images["fight"] = fight
    # A knight's two walking frames facing east, at the fight pose's size and
    # registered with it, STEP_MARGIN right of it, so only what moves changes.
    left, top, _, bottom = facing_reward.getbbox()
    shrink = caster.height / (bottom - top)
    origin = STEP_MARGIN - round(left * shrink), CANVAS - round(bottom * shrink)
    for name, step in (("step1", 0), ("step2", 1)):
        walker = place_pose(walk_phase(group, step), EAST)
        walker = walker.resize((round(CANVAS * shrink), round(CANVAS * shrink)), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (FIGHT_WIDTH, CANVAS))
        canvas.paste(walker, origin)  # Onto an empty canvas: a plain copy, even past its edge.
        images[name] = canvas
    victim = standing.crop(standing.getbbox())
    victim.thumbnail((40, 56), Image.Resampling.LANCZOS)
    cornered = Image.new("RGBA", (FIGHT_WIDTH, CANVAS))
    cornered.alpha_composite(victim, (CORNERED_CENTER - victim.width // 2, CANVAS - 2 - victim.height))
    images["cornered"] = cornered
    # Working: the caster walks east in place. The rail alternates working and working-2.
    images["working-2"] = place_pose(walk_phase(group, 1), EAST)
    steps = shared_crop([poses[walk_phase(group, step), EAST] for step in range(WALK_STEPS)], (40, 56))
    for step, walker in enumerate(steps):
        images[f"walk-{step}"] = standing_at(walker, 0)
    return images


def monster_flee(archive, group):
    """The monster walking away east, in place where it stood, one image per step."""
    poses = [frame(archive, group, walk_phase(group, step), EAST).rotate(-45, resample=Image.Resampling.BICUBIC, expand=True)
             for step in range(WALK_STEPS)]
    steps = shared_crop(poses, (FIGHT_WIDTH - MONSTER_CENTER << 1, 56))
    return [standing_at(image, MONSTER_CENTER - image.width // 2) for image in steps]


def monster_image(archive, group):
    """One monster facing the character, cropped to fit a fight scene."""
    image = frame(archive, group, 0, WEST).rotate(-45, resample=Image.Resampling.BICUBIC, expand=True)
    image = image.crop(image.getbbox())
    image.thumbnail((FIGHT_WIDTH - MONSTER_CENTER << 1, 56), Image.Resampling.LANCZOS)
    return image


def standing_at(image, left):
    """The image on an empty fight scene, on the floor with its left edge at `left`."""
    canvas = Image.new("RGBA", (FIGHT_WIDTH, CANVAS))
    canvas.alpha_composite(image, (left, CANVAS - image.height))
    return canvas


def blood_pool(archive, group, center):
    """Blood on the floor under whoever stands at x `center`."""
    image = frame(archive, group, 0, *BLOOD)
    image = image.crop(image.getbbox())
    image.thumbnail((POOL_SIZE, POOL_SIZE), Image.Resampling.LANCZOS)
    # Flattened to lie on the floor.
    image = image.resize((image.width, round(image.height * 0.7)), Image.Resampling.LANCZOS)
    return standing_at(image, min(center - image.width // 2, FIGHT_WIDTH - image.width))


def corpse_image(archive, group):
    """A dead monster where it stood in the working scene."""
    image = frame(archive, group, 0, 0)
    image = image.crop(image.getbbox())
    image.thumbnail((48, 48), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (FIGHT_WIDTH, CANVAS))
    canvas.alpha_composite(image, (MONSTER_CENTER - image.width // 2, CANVAS - 2 - image.height))
    return canvas


def reward_image(archive, group, x=0, y=0):
    """One loot item lying on the corpse, sized to read against it."""
    image = frame(archive, group, 0, x, y)
    image = image.crop(image.getbbox())
    longer = max(image.size)
    scale = min(max(longer, REWARD_SIZES[0]), REWARD_SIZES[1]) / longer
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    return standing_at(image, min(MONSTER_CENTER - image.width // 2, FIGHT_WIDTH - image.width))


def sleep_frames(archive, group):
    """The Zzz rising beside the sleeping character, one image per phase."""
    images = [frame(archive, group, phase, 0) for phase in range(group["phases"])]
    boxes = [image.getbbox() for image in images if image.getbbox()]
    # Shared bounds keep the letters' movement between phases.
    bounds = (min(box[0] for box in boxes), min(box[1] for box in boxes),
              max(box[2] for box in boxes), max(box[3] for box in boxes))
    scale = min(SLEEP_SIZE[0] / (bounds[2] - bounds[0]), SLEEP_SIZE[1] / (bounds[3] - bounds[1]))
    size = round((bounds[2] - bounds[0]) * scale), round((bounds[3] - bounds[1]) * scale)
    frames = []
    for image in images:
        canvas = Image.new("RGBA", (FIGHT_WIDTH, CANVAS))
        canvas.alpha_composite(image.crop(bounds).resize(size, Image.Resampling.LANCZOS), (SLEEP_LEFT, 2))
        frames.append(canvas)
    return frames


def centered(image, x, y):
    """The image on an empty fight scene, centered at (x, y) and clipped to it."""
    canvas = Image.new("RGBA", (FIGHT_WIDTH, CANVAS))
    canvas.paste(image, (x - image.width // 2, y - image.height // 2))
    return canvas


def spell_frames(archive, missile, effect, level=False):
    """The missile flying east, then the hit on the monster."""
    shot = frame(archive, missile, 0, 2, 1).resize((MISSILE_SIZE, MISSILE_SIZE), Image.Resampling.LANCZOS)
    y = SPELL_HEIGHT
    if level:
        top, bottom = shot.getbbox()[1::2]
        y += (MISSILE_SIZE - top - bottom) // 2
    frames = [centered(shot, round(MISSILE_START + (MONSTER_CENTER - MISSILE_START) * step / (FLIGHT_STEPS - 1)), y)
              for step in range(FLIGHT_STEPS)]
    return frames + hit_frames(archive, effect)


def hit_frames(archive, effect, size=EFFECT_TILE):
    """An effect playing on the monster."""
    frames = []
    width, height = effect["width"], effect["height"]
    for point in HIT_STEPS:
        hit = frame(archive, effect, round((effect["phases"] - 1) * point), 0)
        hit = hit.resize((width * size, height * size), Image.Resampling.LANCZOS)
        # Effects anchor on their bottom-right tile.
        frames.append(centered(hit, MONSTER_CENTER - (width - 1) * size // 2,
                               SPELL_HEIGHT - (height - 1) * size // 2))
    return frames


def item_canvas(archive, group, x=0, y=0):
    """One item, cropped, scaled to read beside the character, bottom-right."""
    width, height = group["width"], group["height"]
    image = Image.new("RGBA", (width * TILE, height * TILE))
    for row in range(height):
        for col in range(width):
            sprite_id = sprite_index(group, 0, x, y, 0, 0, row, col)
            image.alpha_composite(archive.sprite(sprite_id), ((width - 1 - col) * TILE, (height - 1 - row) * TILE))
    image = image.crop(image.getbbox())
    box = (round(29 * SCALE), round(32 * SCALE))
    if max(image.size) > max(box):
        image.thumbnail(box, Image.Resampling.LANCZOS)
    elif max(image.size) < 14:
        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (CANVAS, CANVAS))
    canvas.alpha_composite(image, (CANVAS - image.width, CANVAS - image.height))
    return canvas


def save_sprite(sprites, path, image):
    (sprites / path).parent.mkdir(parents=True, exist_ok=True)
    image.save(sprites / path)
    padded_path = sprites / "padded" / path
    padded_path.parent.mkdir(parents=True, exist_ok=True)
    padded = Image.new("RGBA", (image.width + 2 * EDGE_PADDING, image.height + 2 * EDGE_PADDING))
    padded.paste(image, (EDGE_PADDING, EDGE_PADDING))
    padded.save(padded_path)


def load_table(path, name):
    """Read the numbers of one of the mod's tables, ignoring comments and names."""
    source = re.sub(r'//.*|"[^"]*"', "", path.read_text())
    body = re.search(rf"\b{name}\s*=\s*\[(.*?)\];", source, re.DOTALL)
    if not body:
        raise ValueError(f"No {name} table in {path}")
    return [int(value) for value in re.findall(r"\d+", body.group(1))]


def clear_sprites(sprites, directory):
    for root in (sprites, sprites / "padded"):
        for stale in (root / directory).glob("*.png"):
            stale.unlink()


MOD = Path(__file__).resolve().parent.parent / "mods/agents-tibia"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.home() / "Documents/tibia-8.6")
    parser.add_argument("--sprites", type=Path, default=MOD / "sprites")
    parser.add_argument("--dat-index", type=Path, help="Index from dump-dat-860.py (default: <source>/dat-index.json)")
    parser.add_argument("--loot", type=Path, default=MOD / "loot.js",
                        help="Loot table of the mod (default: mods/agents-tibia/loot.js)")
    parser.add_argument("--fights", type=Path, default=MOD / "fights.js",
                        help="Monster and attack tables of the mod (default: mods/agents-tibia/fights.js)")
    parser.add_argument("--outfits", type=Path, default=MOD / "outfits.js",
                        help="Outfit table of the mod (default: mods/agents-tibia/outfits.js)")
    parser.add_argument("--colors", type=Path,
                        help="Outfit colors from the color page (default: <source>/cores.json; absent: the classic colors)")
    args = parser.parse_args()

    outfits = load_table(args.outfits, "OUTFITS") + load_table(args.outfits, "RETRO")
    # Read first, so a bad color file stops before anything is written.
    default_palette, outfit_palettes = load_colors(args.colors or args.source / "cores.json", set(outfits))
    archive = SpriteArchive(args.source / "Tibia.spr")
    dat = DatIndex(args.dat_index or args.source / "dat-index.json")
    loot = load_table(args.loot, "LOOT")
    monster_ids = load_table(args.fights, "MONSTERS")
    monsters = list(zip(monster_ids[::2], monster_ids[1::2]))
    spell_ids = [number for name in ("SORCERER", "DRUID", "PALADIN") for number in load_table(args.fights, name)]
    spells = list(zip(spell_ids[::2], spell_ids[1::2]))
    if len({missile for missile, _ in spells}) != len(spells):
        raise ValueError(f"A missile id appears twice in {args.fights}")

    attack_group = dat.group("effects", ATTACK_EFFECT)
    attack_ids = [sprite_index(attack_group, phase, 0, 0, 0, 0, 0, 0)
                  for phase in range(attack_group["phases"])]

    loot_images, reward_images = {}, {}
    for item_id in loot:
        x, y = ITEM_FRAMES.get(item_id, (0, 0))
        loot_images[item_id] = item_canvas(archive, dat.group("items", item_id), x, y)
        reward_images[item_id] = reward_image(archive, dat.group("items", item_id), x, y)

    monster_images = {look: monster_image(archive, dat.group("outfits", look)) for look, _ in monsters}
    corpse_images = {look: corpse_image(archive, dat.group("items", corpse)) for look, corpse in monsters}
    pool = blood_pool(archive, dat.group("items", POOL_ITEM), CORNERED_CENTER)
    monster_pool = blood_pool(archive, dat.group("items", POOL_ITEM), MONSTER_CENTER)
    spell_images = {missile: spell_frames(archive, dat.group("missiles", missile), dat.group("effects", effect),
                                          missile in LOW_MISSILES)
                    for missile, effect in spells}
    blood_images = hit_frames(archive, attack_group, BLOOD_SIZE)

    sleep_images = sleep_frames(archive, dat.group("effects", SLEEP_EFFECT))

    sprites = args.sprites
    clear_sprites(sprites, "sleep")
    for phase, image in enumerate(sleep_images):
        save_sprite(sprites, Path("sleep") / f"{phase}.png", image)
    clear_sprites(sprites, "monsters")
    clear_sprites(sprites, "spells")
    clear_sprites(sprites, "blood")
    clear_sprites(sprites, "melee")
    clear_sprites(sprites, "cornered")
    clear_sprites(sprites, "corpses")
    clear_sprites(sprites, "rewards")
    for look, image in corpse_images.items():
        save_sprite(sprites, Path("corpses") / f"{look}.png", image)
    for item_id, image in reward_images.items():
        save_sprite(sprites, Path("rewards") / f"{item_id}.png", image)
    for look, image in monster_images.items():
        save_sprite(sprites, Path("monsters") / f"{look}.png",
                    standing_at(image, MONSTER_CENTER - image.width // 2))
        save_sprite(sprites, Path("melee") / f"{look}.png", standing_at(image, MELEE_LEFT))
        for step, image in enumerate(monster_flee(archive, dat.group("outfits", look))):
            save_sprite(sprites, Path("monsters") / f"{look}-flee-{step}.png", image)
    save_sprite(sprites, Path("cornered") / "pool.png", pool)
    save_sprite(sprites, Path("blood") / "pool.png", monster_pool)
    for step, image in enumerate(blood_images):
        save_sprite(sprites, Path("blood") / f"{step}.png", image)
    for missile, frames in spell_images.items():
        for step, image in enumerate(frames):
            save_sprite(sprites, Path("spells") / f"{missile}-{step}.png", image)

    items = sprites / "done"
    items.mkdir(parents=True, exist_ok=True)
    for stale in items.glob("*.png"):
        stale.unlink()
    padded_items = sprites / "padded" / "done"
    if padded_items.exists():
        for stale in padded_items.glob("*.png"):
            stale.unlink()
    for item_id, image in loot_images.items():
        save_sprite(sprites, Path("done") / f"{item_id}.png", image)

    attack = sprites / "attack"
    attack.mkdir(parents=True, exist_ok=True)
    for stale in attack.glob("*.png"):
        stale.unlink()
    for sprite_id in attack_ids:
        effect_size = round(42 * SCALE)
        effect = archive.sprite(sprite_id).resize((effect_size, effect_size), Image.Resampling.LANCZOS)
        effect.putalpha(effect.getchannel("A").point(lambda alpha: alpha * 4 // 5))
        canvas = Image.new("RGBA", (CANVAS, CANVAS))
        canvas.alpha_composite(effect, ((CANVAS - effect_size) // 2, 0))
        save_sprite(sprites, Path("attack") / f"{sprite_id}.png", canvas)
        burst = archive.sprite(sprite_id).resize((BURST_SIZE, BURST_SIZE), Image.Resampling.LANCZOS)
        burst.putalpha(burst.getchannel("A").point(lambda alpha: alpha * 4 // 5))
        save_sprite(sprites, Path("cornered") / f"{sprite_id}.png",
                    centered(burst, CORNERED_CENTER, CANVAS - 8 - BURST_SIZE // 2))

    sample_ids = [item_id for item_id in PREVIEW_LOOT if item_id in loot_images][:3]
    labels = ("idle", "working", "need_help") + tuple(f"loot {item_id}" for item_id in sample_ids)
    samples = [loot_images[item_id] for item_id in sample_ids]
    preview = Image.new("RGB", (52 + len(labels) * 80, 28 + len(outfits) * 68), "#262626")
    draw = ImageDraw.Draw(preview)
    for col, label in enumerate(labels):
        draw.text((54 + col * 80, 8), label, fill="white")

    with Image.open(attack / f"{attack_ids[0]}.png") as effect:
        preview_effect = effect.copy()

    for row, outfit_id in enumerate(outfits):
        group = dat.group("outfits", outfit_id)
        frames = archive_frames(archive, group)
        save_frame_cache(args.source / "frames", outfit_id, frames, group)
        images = status_images(frames, group, outfit_palettes.get(outfit_id, default_palette))
        directory = sprites / str(outfit_id)
        padded_directory = sprites / "padded" / str(outfit_id)
        for stale in list(directory.glob("done-*.png")) + list(padded_directory.glob("done-*.png")):
            stale.unlink()
        draw.text((16, 53 + row * 68), str(outfit_id), fill="white")
        for label in OUTFIT_LABELS:
            save_sprite(sprites, Path(str(outfit_id)) / f"{label}.png", images[label])
        shown = {
            "idle": images["idle"],
            "working": images["working"],
            "need_help": Image.alpha_composite(images["need_help"], preview_effect),
        }
        for label, sample in zip(labels[3:], samples):
            shown[label] = Image.alpha_composite(images["done"], sample)
        for col, label in enumerate(labels):
            thumbnail = shown[label].resize((64, 64), Image.Resampling.LANCZOS)
            preview.paste(thumbnail, (56 + col * 80, 28 + row * 68), thumbnail)
    preview.save(args.source / "preview-860.png")

    print(f"attack sprite ids: {attack_ids}")
    print(f"wrote {len(outfits)} outfits, {len(loot_images)} loot items, "
          f"{len(monster_images)} monsters, {len(spell_images)} spells, "
          f"and {len(attack_ids)} attack frames to {sprites}")


if __name__ == "__main__":
    main()
