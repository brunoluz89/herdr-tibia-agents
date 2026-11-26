#!/usr/bin/env python3
"""Dump the cip860-extended Tibia.dat into the frame index used by tibia860.py.

The layout is the classic 8.60 one (attribute stream ended by 0xFF, one frame
group per thing) but counts are last IDs, sprite indexes are uint32, and the
file carries the 0x4C2C7993 signature. This mirrors Assets-Editor's
`cip860-extended` export profile. Parsing must consume the file exactly.
"""

import argparse
import json
from pathlib import Path
from struct import unpack_from
import sys

COUNTS = ("items", "outfits", "effects", "missiles")
FIRST_ID = {"items": 100}
PAYLOAD_U16 = {0, 8, 9, 25, 28, 29, 32}   # ground, writable(2), elevated, minimap, help, clothes
PAYLOAD_U16X2 = {21, 24}                  # light, displacement


class Reader:
    def __init__(self, data, pos=0):
        self.data = data
        self.pos = pos

    def u8(self):
        value = self.data[self.pos]
        self.pos += 1
        return value

    def u16(self):
        value = unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return value

    def u32(self):
        value = unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return value


def read_attributes(reader):
    attrs = []
    while True:
        attr = reader.u8()
        if attr == 0xFF:
            return attrs
        attrs.append(attr)
        if attr in PAYLOAD_U16X2:
            reader.pos += 4
        elif attr in PAYLOAD_U16:
            reader.pos += 2


def read_group(reader):
    width = reader.u8()
    height = reader.u8()
    if width == 0 or height == 0:
        raise ValueError("zero sprite dimensions")
    if width > 1 or height > 1:
        reader.u8()  # exact size
    layers = reader.u8()
    pattern_x = reader.u8()
    pattern_y = reader.u8()
    pattern_z = reader.u8()
    phases = reader.u8()
    total = width * height * layers * pattern_x * pattern_y * pattern_z * phases
    if total > 4096:
        raise ValueError(f"implausible sprite count {total}")
    sprites = list(unpack_from(f"<{total}I", reader.data, reader.pos))
    reader.pos += total * 4
    return {
        "width": width,
        "height": height,
        "layers": layers,
        "patternX": pattern_x,
        "patternY": pattern_y,
        "patternZ": pattern_z,
        "phases": phases,
        "sprites": sprites,
    }


def parse(path):
    data = path.read_bytes()
    reader = Reader(data)
    signature = reader.u32()
    counts = {name: reader.u16() for name in COUNTS}
    things = {}
    for name in COUNTS:
        first = FIRST_ID.get(name, 1)
        entries = {}
        for thing_id in range(first, counts[name] + 1):
            read_attributes(reader)
            entries[thing_id] = read_group(reader)
        things[name] = entries
    if reader.pos != len(data):
        raise ValueError(f"parser stopped at {reader.pos:,} of {len(data):,} bytes")
    return signature, counts, things


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dat", type=Path, default=Path.home() / "Documents/tibia-8.6/Tibia.dat")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    try:
        signature, counts, things = parse(args.dat)
    except Exception as error:
        print(f"could not parse {args.dat}: {error}", file=sys.stderr)
        raise SystemExit(1)

    out = args.out or args.dat.with_name("dat-index.json")
    payload = {"signature": f"0x{signature:08X}", "indexWidth": 32, "counts": counts}
    payload.update(things)
    out.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"0x{signature:08X} {counts} -> {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
