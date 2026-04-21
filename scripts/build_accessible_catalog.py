#!/usr/bin/env python3
"""Build the current best combined paint-store-accessible catalog."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCES = [
    ROOT / "data" / "catalogs" / "behr.json",
    ROOT / "data" / "catalogs" / "glidden.json",
    ROOT / "data" / "catalogs" / "ppg.json",
    ROOT / "data" / "catalogs" / "dunn-edwards.json",
    ROOT / "data" / "catalogs" / "valspar.json",
    ROOT / "data" / "catalogs" / "downloadable-palettes" / "sherwin-williams.json",
    ROOT / "data" / "catalogs" / "downloadable-palettes" / "benjamin-moore.json",
]

OUT = ROOT / "data" / "catalogs" / "paint-store-accessible.json"


def main() -> int:
    records: list[dict] = []
    seen: set[str] = set()
    for source in SOURCES:
        for record in json.loads(source.read_text(encoding="utf-8")):
            key = f"{record['manufacturer']}::{record['brandCode']}"
            if key in seen:
                continue
            seen.add(key)
            records.append(record)

    records.sort(key=lambda record: (record["manufacturer"], record["brandCode"], record["displayName"]))
    OUT.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
