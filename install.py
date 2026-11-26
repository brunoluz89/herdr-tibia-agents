#!/usr/bin/env python3
"""Install or update the Tibia agents panel in this computer's Herdr app.

Copies mods/agents-tibia into the Herdr home, checks it, and writes the
`tibia` layout: this installation's shipped `main` layout with its Agents
block set to the mod. Whatever it replaces is backed up first. It needs only
the Python standard library and `herdr-app`.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import NamedTemporaryFile

MOD = "agents-tibia"
SOURCE = Path(__file__).resolve().parent / "mods" / MOD
# The per-agent outfit and color picker: its own mod, so rewriting the panel's sprites
# (which reloads the panel) doesn't reload the open dialog.
PICKER = "tibia-picker"
PICKER_SOURCE = SOURCE.parent / PICKER


def walk(block):
    yield block
    for child in block.get("children", []):
        yield from walk(child)


def tibia_layout(main):
    """The shipped layout with the mod in place of its Agents block."""
    layout = json.loads(main.read_text())
    matches = [block for block in walk(layout) if block.get("id") == "agents"]
    if len(matches) != 1 or matches[0].get("content", {}).get("mod") != "agents":
        raise SystemExit("The shipped Agents block changed. Inspect main.json before installing.")
    matches[0]["content"]["mod"] = MOD
    return layout


def write_json(path, value):
    with NamedTemporaryFile(mode="w", dir=path.parent, prefix=".tibia-", delete=False) as file:
        json.dump(value, file, indent=2, ensure_ascii=False)
        file.write("\n")
    Path(file.name).replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home() / ".config/herdr-app",
                        help="Herdr home (default: ~/.config/herdr-app)")
    home = parser.parse_args().home

    if not (SOURCE / "sprites").is_dir():
        raise SystemExit(f"No sprites in {SOURCE}. Generate them first; see README.md.")
    if not shutil.which("herdr-app"):
        raise SystemExit("herdr-app is not on PATH.")
    shipped = home / "layouts/main.json"
    if not shipped.is_file():
        raise SystemExit(f"{shipped} is missing. Start Herdr once, or pass --home.")
    # Fail on a changed layout before anything is written.
    layout = tibia_layout(shipped)

    # The picker keeps a copy of the outfit table: a mod can't import another mod's code.
    copy = (PICKER_SOURCE / "outfits.js").read_text(encoding="utf-8").split("\n", 1)[1]
    if copy != (SOURCE / "outfits.js").read_text(encoding="utf-8"):
        raise SystemExit(f"{PICKER}/outfits.js differs from {MOD}/outfits.js: copy it over (keep its first line).")

    # Checked here, so a broken copy never replaces a working one.
    subprocess.run(["herdr-app", "check", str(SOURCE)], check=True)
    subprocess.run(["herdr-app", "check", str(PICKER_SOURCE)], check=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    # Backups stay outside mods/, where Herdr would load them as mods.
    backup = home / "backups" / f"{MOD}-{stamp}"
    target = home / "mods" / MOD
    layout_file = home / "layouts/tibia.json"
    picker = home / "mods" / PICKER
    if target.exists():
        shutil.copytree(target, backup / MOD)
    if picker.exists():
        shutil.copytree(picker, backup / PICKER)
    picker.mkdir(parents=True, exist_ok=True)
    for path in PICKER_SOURCE.iterdir():
        if path.is_file():
            shutil.copy2(path, picker / path.name)
    # The picker runs tools/recolor.py from this repo with this Python.
    (picker / "config.js").write_text("".join((
        "// Written by install.py.", chr(10),
        f"export const REPO = {json.dumps(SOURCE.parent.parent.as_posix())};", chr(10),
        f"export const PYTHON = {json.dumps(Path(sys.executable).as_posix())};", chr(10),
    )), encoding="utf-8")
    if layout_file.exists():
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(layout_file, backup / layout_file.name)

    target.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(target / "sprites", ignore_errors=True)
    # Art first and main.js last: Herdr reloads the mod while files arrive.
    shutil.copytree(SOURCE / "sprites", target / "sprites")
    files = sorted((path for path in SOURCE.iterdir() if path.is_file()), key=lambda path: path.name == "main.js")
    for path in files:
        shutil.copy2(path, target / path.name)
    write_json(layout_file, layout)

    if backup.exists():
        print(f"Previous files saved in {backup}")
    print("Installed. Switch to it with:\n  herdr-app do layout.switch '{\"name\":\"tibia\"}'")


if __name__ == "__main__":
    main()
