#!/usr/bin/env python3
"""Print catalog coverage and caveat stats."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def count_json(path: str) -> int:
    return len(json.loads((ROOT / path).read_text(encoding="utf-8")))


def ppg_skipped() -> int:
    path = ROOT / "data" / "raw" / "ppg" / "detail-pages.jsonl"
    if not path.exists():
        return 0
    skipped = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item.get("record") is None or "error" in item:
            skipped += 1
    return skipped


def main() -> int:
    rows = [
        ("Behr", "official catalog", "data/catalogs/behr.json", "deduped first-party ColorSmart payload"),
        ("Glidden", "official catalog", "data/catalogs/glidden.json", "official sitemap/detail pages"),
        ("PPG Paints", "official catalog", "data/catalogs/ppg.json", f"official sitemap/detail pages; {ppg_skipped()} pages skipped with no RGB"),
        ("Dunn-Edwards", "official catalog", "data/catalogs/dunn-edwards.json", "official digital swatch assets"),
        ("Valspar", "official catalog", "data/catalogs/valspar.json", "official browse-colors page"),
        ("Sherwin-Williams", "official downloadable", "data/catalogs/downloadable-palettes/sherwin-williams.json", "official ASE downloads; not claimed as full live catalog"),
        ("Benjamin Moore", "official downloadable", "data/catalogs/downloadable-palettes/benjamin-moore.json", "official ASE downloads; not claimed as exact full live catalog"),
        ("Combined", "best-current merged", "data/catalogs/paint-store-accessible.json", "one current best source per target brand"),
    ]

    print("| Brand | Source layer | Records | Notes |")
    print("|---|---:|---:|---|")
    for brand, layer, path, notes in rows:
        print(f"| {brand} | {layer} | {count_json(path):,} | {notes} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
