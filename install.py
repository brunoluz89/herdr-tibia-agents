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
from tempfile import NamedTemporaryFile

MOD = "agents-tibia"
SOURCE = Path(__file__).resolve().parent / "mods" / MOD


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

    # Checked here, so a broken copy never replaces a working one.
    subprocess.run(["herdr-app", "check", str(SOURCE)], check=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    # Backups stay outside mods/, where Herdr would load them as mods.
    backup = home / "backups" / f"{MOD}-{stamp}"
    target = home / "mods" / MOD
    layout_file = home / "layouts/tibia.json"
    if target.exists():
        shutil.copytree(target, backup / MOD)
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
