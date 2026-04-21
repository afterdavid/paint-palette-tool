#!/usr/bin/env python3
"""Import official paint color catalogs into normalized JSON.

Current manufacturer support:
- benjamin-moore: uses official sitemap + public color detail pages
- sherwin-williams: uses official family page model JSON + shared-color-service graph crawl

This script preserves raw captures under data/raw/<manufacturer>/ and writes
normalized records to data/catalogs/<manufacturer>.json.

It is intentionally conservative:
- Benjamin Moore can be imported from its official colors sitemap.
- Sherwin-Williams currently performs an official graph crawl seeded from
  family pages and related-color links. This is useful and repeatable, but not
  yet guaranteed complete.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import math
import re
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CATALOG_DIR = DATA_DIR / "catalogs"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "paint-palette-tool/0.1 (+catalog importer)",
        "Accept-Language": "en-US,en;q=0.9",
    }
)

BM_SITEMAP_URL = "https://www.benjaminmoore.com/sitemaps/colors.xml"
SW_SITEMAP_URL = "https://www.sherwin-williams.com/sitemap.xml"
SW_FAMILY_SLUGS = ["blue", "green", "neutral", "orange", "purple", "red", "white", "yellow"]
SW_API_BASE = "https://api.sherwin-williams.com/shared-color-service"


@dataclass
class ImportStats:
    fetched: int = 0
    parsed: int = 0
    written: int = 0
    skipped: int = 0


def fetch_text(url: str, timeout: int = 30) -> str:
    resp = SESSION.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def fetch_json(url: str, timeout: int = 30) -> Any:
    resp = SESSION.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def hex_to_lab(rgb_hex: str) -> dict[str, float]:
    rgb_hex = rgb_hex.lstrip("#")
    r = int(rgb_hex[0:2], 16) / 255.0
    g = int(rgb_hex[2:4], 16) / 255.0
    b = int(rgb_hex[4:6], 16) / 255.0

    def srgb_to_linear(c: float) -> float:
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    r, g, b = map(srgb_to_linear, (r, g, b))

    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    x /= 0.95047
    y /= 1.00000
    z /= 1.08883

    def f(t: float) -> float:
        delta = 6 / 29
        if t > delta**3:
            return t ** (1 / 3)
        return t / (3 * delta**2) + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    l = 116 * fy - 16
    a = 500 * (fx - fy)
    b2 = 200 * (fy - fz)
    return {"l": round(l, 4), "a": round(a, 4), "b": round(b2, 4)}


def extract_next_build_id(html: str) -> str | None:
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if not match:
        return None
    data = json.loads(match.group(1))
    return data.get("buildId")


def load_bm_color_payload_from_next_json(data: dict[str, Any]) -> dict[str, Any] | None:
    components = (
        data.get("pageProps", {})
        .get("componentData", {})
        .get("components", [])
    )
    for component in components:
        color_data = component.get("color_data", {})
        color = color_data.get("props", {}).get("color")
        if color and color.get("name") and color.get("hex"):
            return color_data.get("props", {})
    return None


def normalize_bm_record(url: str, props: dict[str, Any]) -> dict[str, Any] | None:
    color = props.get("color", {})
    code = str(color.get("color_number") or color.get("number") or "").strip()
    name = str(color.get("name") or "").strip()
    hex_value = str(color.get("hex") or "").strip().upper().lstrip("#")
    if not (code and name and re.fullmatch(r"[0-9A-F]{6}", hex_value)):
        return None
    detail_collections = [c for c in color.get("palettes", []) if isinstance(c, str)]
    if not detail_collections:
        detail_collections = [str(c.get("name")) for c in color.get("palettes", []) if isinstance(c, dict) and c.get("name")]
    return {
        "id": f"benjamin-moore-{slugify(code + '-' + name)}",
        "displayName": name,
        "manufacturer": "Benjamin Moore",
        "brand": "Benjamin Moore",
        "brandCode": code,
        "libraryType": "native",
        "rgbHex": f"#{hex_value}",
        "lab": hex_to_lab(hex_value),
        "source": {
            "kind": "official",
            "url": url,
            "notes": "Imported from Benjamin Moore official colors sitemap and public color detail page.",
        },
        "stockMatchable": True,
        "availabilityNotes": None,
        "aliases": [],
        "catalogOrder": None,
        "active": True,
        "sourceConfidence": "high",
        "lastVerifiedAt": time.strftime("%Y-%m-%d"),
        "regions": ["US"],
        "tags": [tag for tag in detail_collections if isinstance(tag, str)],
    }


def import_benjamin_moore(limit: int | None = None, workers: int = 12) -> ImportStats:
    raw_dir = RAW_DIR / "benjamin-moore"
    ensure_dir(raw_dir)
    ensure_dir(CATALOG_DIR)
    stats = ImportStats()

    sitemap_xml = fetch_text(BM_SITEMAP_URL, timeout=60)
    (raw_dir / "colors-sitemap.xml").write_text(sitemap_xml, encoding="utf-8")

    seed_html = fetch_text("https://www.benjaminmoore.com/en-us/paint-colors", timeout=40)
    build_id = extract_next_build_id(seed_html)
    if not build_id:
        raise RuntimeError("Could not determine Benjamin Moore Next.js build id")
    (raw_dir / "next-build-id.txt").write_text(build_id + "\n", encoding="utf-8")

    urls = re.findall(r"<loc>(https://www\.benjaminmoore\.com/en-us/paint-colors/color/[^<]+)</loc>", sitemap_xml)
    urls = sorted(dict.fromkeys(urls))
    if limit:
        urls = urls[:limit]
    (raw_dir / "detail-urls.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")

    raw_jsonl_path = raw_dir / "detail-pages.jsonl"
    normalized: list[dict[str, Any]] = []

    def worker(url: str) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
        parsed = urlparse(url)
        json_url = f"https://www.benjaminmoore.com/_next/data/{build_id}{parsed.path}.json"
        data = fetch_json(json_url, timeout=40)
        props = load_bm_color_payload_from_next_json(data)
        record = normalize_bm_record(url, props or {}) if props else None
        raw_entry = {"url": url, "jsonUrl": json_url, "props": props}
        return url, raw_entry, record

    with raw_jsonl_path.open("w", encoding="utf-8") as raw_f:
        with futures.ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(worker, url): url for url in urls}
            for future in futures.as_completed(future_map):
                url = future_map[future]
                try:
                    _, raw_entry, record = future.result()
                except Exception as exc:
                    stats.skipped += 1
                    raw_f.write(json.dumps({"url": url, "error": str(exc)}, ensure_ascii=False) + "\n")
                    continue
                stats.fetched += 1
                raw_f.write(json.dumps(raw_entry, ensure_ascii=False) + "\n")
                if record:
                    normalized.append(record)
                    stats.parsed += 1
                else:
                    stats.skipped += 1

    normalized.sort(key=lambda r: (r["brandCode"], r["displayName"]))
    (CATALOG_DIR / "benjamin-moore.json").write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    stats.written = len(normalized)
    return stats


def extract_sw_codes_from_object(obj: Any) -> set[str]:
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for v in value.values():
                visit(v)
        elif isinstance(value, list):
            for v in value:
                visit(v)
        elif isinstance(value, str):
            for match in re.findall(r"\bSW\s?(\d{4})\b", value, flags=re.I):
                found.add(f"SW{match}")
            for match in re.findall(r"/sw(\d{4})-[a-z0-9-]+", value, flags=re.I):
                found.add(f"SW{match}")
            for match in re.findall(r"sw-(\d{4})", value, flags=re.I):
                found.add(f"SW{match}")

    visit(obj)
    return found


def normalize_sw_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    code = str(raw.get("colorNumber") or "").strip().upper()
    name = str(raw.get("name") or "").strip()
    hex_value = str(raw.get("hex") or "").strip().upper().lstrip("#")
    if not (re.fullmatch(r"SW\d{4}", code) and name and re.fullmatch(r"[0-9A-F]{6}", hex_value)):
        return None
    related_families = [str(v) for v in raw.get("colorFamilyNames", []) if v]
    notes = "Imported from Sherwin-Williams official family page model JSON and shared-color-service graph crawl. Coverage is partial until a complete official enumeration endpoint is confirmed."
    return {
        "id": f"sherwin-williams-{slugify(code + '-' + name)}",
        "displayName": name,
        "manufacturer": "Sherwin-Williams",
        "brand": "Sherwin-Williams",
        "brandCode": code,
        "libraryType": "native",
        "rgbHex": f"#{hex_value}",
        "lab": hex_to_lab(hex_value),
        "source": {
            "kind": "official",
            "url": f"{SW_API_BASE}/color/byColorNumber/{code}",
            "notes": notes,
        },
        "stockMatchable": True,
        "availabilityNotes": "Partial official crawl; do not treat current catalog file as complete Sherwin-Williams coverage yet.",
        "aliases": [],
        "catalogOrder": raw.get("displayOrder"),
        "active": str(raw.get("status") or "ACTIVE").upper() != "INACTIVE",
        "sourceConfidence": "medium",
        "lastVerifiedAt": time.strftime("%Y-%m-%d"),
        "regions": ["US"],
        "tags": related_families,
    }


def import_sherwin_williams(max_records: int = 1200) -> ImportStats:
    raw_dir = RAW_DIR / "sherwin-williams"
    ensure_dir(raw_dir)
    ensure_dir(CATALOG_DIR)
    stats = ImportStats()

    sitemap_xml = fetch_text(SW_SITEMAP_URL, timeout=60)
    (raw_dir / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")

    family_models: dict[str, Any] = {}
    seed_codes: set[str] = set()
    for slug in SW_FAMILY_SLUGS:
        model_url = f"https://www.sherwin-williams.com/en-us/color/color-family/{slug}-paint-colors/_jcr_content/root/container/color_by_group_grid.model.json"
        data = fetch_json(model_url, timeout=30)
        family_models[slug] = {"modelUrl": model_url, "data": data}
        seed_codes.update(extract_sw_codes_from_object(data))
    (raw_dir / "family-models.json").write_text(json.dumps(family_models, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (raw_dir / "seed-codes.txt").write_text("\n".join(sorted(seed_codes)) + "\n", encoding="utf-8")

    queue = deque(sorted(seed_codes))
    seen: set[str] = set(queue)
    raw_entries: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []

    while queue and len(normalized) < max_records:
        code = queue.popleft()
        try:
            payload = fetch_json(f"{SW_API_BASE}/color/byColorNumber/{code}", timeout=30)
        except Exception:
            stats.skipped += 1
            continue
        stats.fetched += 1
        raw_entries.append(payload)
        record = normalize_sw_record(payload)
        if record:
            normalized.append(record)
            stats.parsed += 1
        else:
            stats.skipped += 1
            continue
        for bucket in ("colorStripColors", "similarColors", "coordinatingColors"):
            for item in payload.get(bucket, []) or []:
                next_code = str(item.get("number") or item.get("colorNumber") or "").strip().upper()
                if re.fullmatch(r"SW\d{4}", next_code) and next_code not in seen:
                    seen.add(next_code)
                    queue.append(next_code)

    (raw_dir / "crawl-records.json").write_text(json.dumps(raw_entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    normalized = list({rec["brandCode"]: rec for rec in normalized}.values())
    normalized.sort(key=lambda r: (r["brandCode"], r["displayName"]))
    (CATALOG_DIR / "sherwin-williams.json").write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    stats.written = len(normalized)
    return stats


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manufacturer", choices=["benjamin-moore", "sherwin-williams", "all"])
    parser.add_argument("--limit", type=int, default=None, help="Limit records/pages for Benjamin Moore")
    parser.add_argument("--sw-max-records", type=int, default=1200)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args(argv)

    results: dict[str, ImportStats] = {}
    if args.manufacturer in {"benjamin-moore", "all"}:
        results["benjamin-moore"] = import_benjamin_moore(limit=args.limit, workers=args.workers)
    if args.manufacturer in {"sherwin-williams", "all"}:
        results["sherwin-williams"] = import_sherwin_williams(max_records=args.sw_max_records)

    for name, stats in results.items():
        print(f"{name}: fetched={stats.fetched} parsed={stats.parsed} written={stats.written} skipped={stats.skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
