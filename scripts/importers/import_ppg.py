#!/usr/bin/env python3
"""Import PPG Paints colors from first-party sitemap/detail pages.

PPG's downloadable ACO/ASE/XLS links currently point at hosts that do not
resolve from this machine. The public color detail pages are live, first-party,
and expose name, brand code, RGB, and LRV, so this importer uses them as the
canonical PPG catalog source.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import html
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "ppg"
CATALOG_DIR = ROOT / "data" / "catalogs"
SITEMAP_URL = "https://www.ppgpaints.com/sitemap.xml"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "paint-palette-tool/0.1 (+PPG catalog importer)",
        "Accept-Language": "en-US,en;q=0.9",
    }
)


@dataclass
class ImportStats:
    urls: int = 0
    fetched: int = 0
    parsed: int = 0
    skipped: int = 0


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def rgb_to_lab(r: int, g: int, b: int) -> dict[str, float]:
    rr, gg, bb = (r / 255.0, g / 255.0, b / 255.0)

    def srgb_to_linear(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    rr, gg, bb = map(srgb_to_linear, (rr, gg, bb))
    x = rr * 0.4124564 + gg * 0.3575761 + bb * 0.1804375
    y = rr * 0.2126729 + gg * 0.7151522 + bb * 0.0721750
    z = rr * 0.0193339 + gg * 0.1191920 + bb * 0.9503041
    x /= 0.95047
    y /= 1.00000
    z /= 1.08883

    def f(value: float) -> float:
        delta = 6 / 29
        if value > delta**3:
            return value ** (1 / 3)
        return value / (3 * delta**2) + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    return {
        "l": round(116 * fy - 16, 4),
        "a": round(500 * (fx - fy), 4),
        "b": round(200 * (fy - fz), 4),
    }


def fetch_text(url: str, timeout: int = 40) -> str:
    response = SESSION.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def color_urls_from_sitemap(xml: str) -> list[str]:
    urls = re.findall(r"<loc>(https://www\.ppgpaints\.com/ppg-colors/[^<]+)</loc>", xml)
    return sorted(dict.fromkeys(urls))


def parse_detail_page(url: str, body: str) -> dict[str, Any] | None:
    title_match = re.search(r"<title>\s*(.*?)\s+-\s+(.*?)\s+Paint Color\s+\|\s+PPG Paints\s*</title>", body, re.I | re.S)
    name_match = re.search(r'<h1[^>]*class="[^"]*heading-style-h2[^"]*"[^>]*>(.*?)</h1>', body, re.I | re.S)
    code_match = re.search(r'<p[^>]*class="[^"]*heading-style-h6[^"]*"[^>]*>(.*?)</p>', body, re.I | re.S)
    rgb_match = re.search(
        r"<b>R:</b>\s*(\d{1,3})\s*<b>G:</b>\s*(\d{1,3})\s*<b>B:</b>\s*(\d{1,3})\s*<b>LRV:</b>\s*([0-9.]+)",
        body,
        re.I,
    )
    if not rgb_match:
        rgb_match = re.search(r"background-color:\s*rgb\((\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\)", body, re.I)

    if title_match:
        display_name = html.unescape(title_match.group(1)).strip()
        brand_code = html.unescape(title_match.group(2)).strip()
    elif name_match and code_match:
        display_name = html.unescape(re.sub(r"<[^>]+>", "", name_match.group(1))).strip()
        brand_code = html.unescape(re.sub(r"<[^>]+>", "", code_match.group(1))).strip()
    else:
        return None

    if not rgb_match:
        return None

    r, g, b = [int(rgb_match.group(i)) for i in range(1, 4)]
    if not all(0 <= channel <= 255 for channel in (r, g, b)):
        return None
    lrv = float(rgb_match.group(4)) if rgb_match.lastindex and rgb_match.lastindex >= 4 else None

    rgb_hex = f"#{r:02X}{g:02X}{b:02X}"
    return {
        "id": f"ppg-{slugify(brand_code + '-' + display_name)}",
        "displayName": display_name,
        "manufacturer": "PPG Paints",
        "brand": "PPG Paints",
        "brandCode": brand_code,
        "libraryType": "native",
        "rgbHex": rgb_hex,
        "lab": rgb_to_lab(r, g, b),
        "source": {
            "kind": "official",
            "url": url,
            "notes": "Imported from PPG Paints official sitemap and public color detail page. PPG's official downloadable palette asset links were present but not DNS-resolvable during this pass.",
        },
        "stockMatchable": True,
        "lrv": lrv,
        "availabilityNotes": "Imported from the currently published PPG Paints public color pages; treat as current first-party web catalog coverage, not historical discontinued-color coverage.",
        "aliases": [],
        "catalogOrder": None,
        "active": True,
        "sourceConfidence": "high",
        "lastVerifiedAt": time.strftime("%Y-%m-%d"),
        "regions": ["US"],
        "tags": [],
    }


def import_ppg(limit: int | None = None, workers: int = 16) -> ImportStats:
    ensure_dir(RAW_DIR)
    ensure_dir(CATALOG_DIR)
    stats = ImportStats()

    sitemap_xml = fetch_text(SITEMAP_URL, timeout=60)
    (RAW_DIR / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")
    urls = color_urls_from_sitemap(sitemap_xml)
    if limit:
        urls = urls[:limit]
    stats.urls = len(urls)
    (RAW_DIR / "detail-urls.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")

    raw_jsonl_path = RAW_DIR / "detail-pages.jsonl"
    records: list[dict[str, Any]] = []

    def worker(url: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
        body = fetch_text(url)
        record = parse_detail_page(url, body)
        return {"url": url, "record": record}, record

    with raw_jsonl_path.open("w", encoding="utf-8") as raw_f:
        with futures.ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(worker, url): url for url in urls}
            for future in futures.as_completed(future_map):
                url = future_map[future]
                try:
                    raw_entry, record = future.result()
                except Exception as exc:
                    stats.skipped += 1
                    raw_f.write(json.dumps({"url": url, "error": str(exc)}, ensure_ascii=False) + "\n")
                    continue
                stats.fetched += 1
                raw_f.write(json.dumps(raw_entry, ensure_ascii=False) + "\n")
                if record:
                    records.append(record)
                    stats.parsed += 1
                else:
                    stats.skipped += 1

    merged = {record["id"]: record for record in records}
    records = sorted(merged.values(), key=lambda record: (record["displayName"].lower(), record["brandCode"]))
    (CATALOG_DIR / "ppg.json").write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    stats = import_ppg(limit=args.limit, workers=args.workers)
    print(f"ppg: urls={stats.urls} fetched={stats.fetched} parsed={stats.parsed} skipped={stats.skipped}")
    return 0 if stats.parsed else 1


if __name__ == "__main__":
    raise SystemExit(main())
