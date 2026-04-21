#!/usr/bin/env python3
"""Generate an Adobe Swatch Exchange file from catalog JSON."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


def rgb_hex_to_float_triplet(rgb_hex: str) -> tuple[float, float, float]:
    rgb_hex = rgb_hex.strip().lstrip("#")
    if len(rgb_hex) != 6:
        raise ValueError(f"Invalid RGB hex: {rgb_hex}")
    return (
        int(rgb_hex[0:2], 16) / 255.0,
        int(rgb_hex[2:4], 16) / 255.0,
        int(rgb_hex[4:6], 16) / 255.0,
    )


def utf16be_name(value: str) -> bytes:
    # ASE stores the string length as UTF-16 code units including the null.
    return (value + "\0").encode("utf-16-be")


def color_block(name: str, rgb_hex: str) -> bytes:
    encoded_name = utf16be_name(name)
    payload = (
        struct.pack(">H", len(encoded_name) // 2)
        + encoded_name
        + b"RGB "
        + struct.pack(">fff", *rgb_hex_to_float_triplet(rgb_hex))
        + struct.pack(">H", 0)
    )
    return struct.pack(">HI", 0x0001, len(payload)) + payload


def write_ase(records: list[dict], out_path: Path, name_format: str) -> None:
    blocks: list[bytes] = []
    for record in records:
        rgb_hex = record.get("rgbHex")
        if not rgb_hex:
            continue
        name = name_format.format(
            displayName=record.get("displayName", ""),
            brandCode=record.get("brandCode", ""),
            manufacturer=record.get("manufacturer", ""),
            brand=record.get("brand", ""),
        ).strip()
        blocks.append(color_block(name, rgb_hex))

    header = b"ASEF" + struct.pack(">HHI", 1, 0, len(blocks))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(header + b"".join(blocks))


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default=str(repo_root / "data" / "seed-palette.example.json"))
    parser.add_argument("output", nargs="?", default=str(repo_root / "ase" / "seed-palette-v1.ase"))
    parser.add_argument("--name-format", default="{brandCode} {displayName}")
    args = parser.parse_args()

    data_path = Path(args.input)
    out_path = Path(args.output)

    if not data_path.exists():
        print(f"Missing palette input: {data_path}", file=sys.stderr)
        return 1

    with data_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    write_ase(records, out_path, args.name_format)

    print(f"Wrote {len(records)} colors to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
