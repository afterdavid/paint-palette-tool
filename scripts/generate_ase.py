#!/usr/bin/env python3
"""Generate an Adobe Swatch Exchange file from palette JSON.

Current status:
- scaffold only
- validates input path assumptions
- writes a placeholder output note until ASE serialization is implemented

This script exists to lock in the build path:
seed palette JSON -> ASE generator -> Illustrator swatch library
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    data_path = repo_root / "data" / "seed-palette.example.json"
    out_dir = repo_root / "ase"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "seed-palette-v1.placeholder.txt"

    if not data_path.exists():
        print(f"Missing palette input: {data_path}", file=sys.stderr)
        return 1

    with data_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    out_path.write_text(
        "Paint Palette Tool ASE generator placeholder\n"
        f"Loaded {len(records)} records from {data_path.name}.\n"
        "Next step: implement real ASE binary serialization.\n",
        encoding="utf-8",
    )

    print(f"Wrote placeholder output to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
