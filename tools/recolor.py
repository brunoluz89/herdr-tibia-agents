#!/usr/bin/env python3
"""Recolor one outfit from the frames tibia860.py cached, fast enough for the picker.

  --preview <png>   writes a preview of the outfit in these colors (standing, then walking)
  --apply           writes the outfit's sprites into each --sprites folder and saves the
                    colors in cores.json; --reset does the same with the default colors and
                    drops the outfit from cores.json

Colors are hex: --cabeca #ffaa00 --corpo ... Missing parts keep cores.json's "todos".
"""

import argparse
import json
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tibia860  # noqa: E402

SOURCE = Path.home() / "Documents/tibia-8.6"


def cached_frames(cache, outfit_id):
    folder = cache / str(outfit_id)
    group = json.loads((folder / "group.json").read_text(encoding="utf-8"))
    loaded = {}

    def frames(phase, direction, addon, layer):
        key = (phase, direction, addon, layer)
        if key not in loaded:
            with Image.open(folder / f"{phase}-{direction}-{addon}-{layer}.png") as image:
                loaded[key] = image.convert("RGBA")
        return loaded[key]
    return frames, group


def preview(frames, group, palette, out):
    """The standing pose and a walking step, big enough to judge colors."""
    poses = [tibia860.rotated_frame(frames, group, 0, tibia860.SOUTH, palette),
             tibia860.rotated_frame(frames, group, tibia860.walk_phase(group, 0), tibia860.EAST, palette)]
    poses = tibia860.shared_crop(poses, (64, 64))
    sheet = Image.new("RGBA", (128, 64))
    for index, pose in enumerate(poses):
        sheet.alpha_composite(pose, (index * 64 + (64 - pose.width) // 2, 64 - pose.height))
    out.parent.mkdir(parents=True, exist_ok=True)
    # Older previews go: each render has its own name, so no image cache gets in the way.
    for stale in out.parent.glob("*.png"):
        if stale != out:
            stale.unlink(missing_ok=True)
    sheet.save(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outfit", type=int, required=True)
    for part in tibia860.PARTS:
        parser.add_argument(f"--{part}")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--sprites", type=Path, action="append", default=[])
    args = parser.parse_args()

    colors_file = args.source / "cores.json"
    data = json.loads(colors_file.read_text(encoding="utf-8")) if colors_file.is_file() else {}
    chosen = {part: getattr(args, part) for part in tibia860.PARTS if getattr(args, part)}
    default = tibia860.parse_palette(data.get("todos", {}), tibia860.PALETTE)
    palette = default if args.reset else tibia860.parse_palette(chosen, default)
    frames, group = cached_frames(args.source / "frames", args.outfit)

    if args.preview:
        preview(frames, group, palette, args.preview)
    if args.apply or args.reset:
        images = tibia860.status_images(frames, group, palette)
        for sprites in args.sprites:
            for label in tibia860.OUTFIT_LABELS:
                tibia860.save_sprite(sprites, Path(str(args.outfit)) / f"{label}.png", images[label])
        outfits = data.setdefault("outfits", {})
        if args.reset:
            outfits.pop(str(args.outfit), None)
        else:
            outfits[str(args.outfit)] = {part: value.lower() for part, value in chosen.items()}
        colors_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
