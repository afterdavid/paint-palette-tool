#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CATALOG_DIR = ROOT / "data" / "catalogs"
SCHEMA_PATH = ROOT / "data" / "color-schema.json"

BEHR_ALL_JS_URL = "https://www.behr.com/mainrefreshservice/services/color2019/all.js"
GLIDDEN_HOME_URL = "https://www.glidden.com/"
GLIDDEN_SITEMAP_URL = "https://www.glidden.com/sitemap.xml"
GLIDDEN_ALGOLIA_APP_ID = "EU3MF6Q69W"
GLIDDEN_ALGOLIA_SEARCH_KEY = "43fe81ad063e4491bfb68c0e3f55f464"
GLIDDEN_ALGOLIA_INDEX = "prd_Glidden11Colors"

USER_AGENT = "paint-palette-tool/0.1 (+https://github.com/theo/paint-palette-tool)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


@dataclass
class ImportSummary:
    manufacturer: str
    raw_files: list[str]
    record_count: int
    notes: list[str]


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)


def srgb_channel_to_linear(value: float) -> float:
    value = value / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def rgb_to_lab(r: int, g: int, b: int) -> dict[str, float]:
    rl = srgb_channel_to_linear(r)
    gl = srgb_channel_to_linear(g)
    bl = srgb_channel_to_linear(b)

    x = rl * 0.4124564 + gl * 0.3575761 + bl * 0.1804375
    y = rl * 0.2126729 + gl * 0.7151522 + bl * 0.0721750
    z = rl * 0.0193339 + gl * 0.1191920 + bl * 0.9503041

    # D65 reference white
    xr = x / 0.95047
    yr = y / 1.00000
    zr = z / 1.08883

    def f(t: float) -> float:
        delta = 6 / 29
        if t > delta ** 3:
            return t ** (1 / 3)
        return t / (3 * delta ** 2) + 4 / 29

    fx = f(xr)
    fy = f(yr)
    fz = f(zr)

    return {
        "l": round(116 * fy - 16, 4),
        "a": round(500 * (fx - fy), 4),
        "b": round(200 * (fy - fz), 4),
    }


def rgb_triplet_to_hex(rgb_triplet: str) -> str:
    parts = [int(part.strip()) for part in rgb_triplet.split(",")]
    if len(parts) != 3:
        raise ValueError(f"Expected RGB triplet, got: {rgb_triplet}")
    return "#" + "".join(f"{part:02X}" for part in parts)


def sanitize_id(*parts: str) -> str:
    return "-".join(
        re.sub(r"[^a-z0-9]+", "-", part.lower()).strip("-")
        for part in parts
        if part
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def fetch_text(url: str) -> str:
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def fetch_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, payload: Any | None = None) -> Any:
    response = SESSION.request(method, url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def import_behr() -> ImportSummary:
    manufacturer = "behr"
    raw_dir = RAW_DIR / manufacturer
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_js = fetch_text(BEHR_ALL_JS_URL)
    raw_js_path = raw_dir / "all.js"
    raw_js_path.write_text(raw_js)

    match = re.search(r"var\s+colorData\s*=\s*(\[.*\]);?\s*$", raw_js, re.S)
    if not match:
        raise RuntimeError("Could not locate Behr colorData array in all.js")

    rows = json.loads(match.group(1))
    header = rows[0]
    entries = [dict(zip(header, row)) for row in rows[1:]]

    raw_records_path = raw_dir / "all.parsed.json"
    write_json(raw_records_path, {
        "fetchedAt": iso_now(),
        "sourceUrl": BEHR_ALL_JS_URL,
        "fieldOrder": header,
        "count": len(entries),
        "records": entries,
    })

    catalog: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        rgb_hex = entry["rgb"].upper()
        lab = {
            "l": round(float(entry["luminosity"]), 4),
            "a": round(float(entry["a"]), 4),
            "b": round(float(entry["b"]), 4),
        }
        record = {
            "id": sanitize_id("behr", entry["id"]),
            "displayName": entry["name"].title() if entry["name"].isupper() else entry["name"],
            "manufacturer": "Behr",
            "brand": "Behr",
            "brandCode": entry["id"],
            "libraryType": "native",
            "rgbHex": rgb_hex,
            "lab": lab,
            "source": {
                "kind": "official",
                "url": BEHR_ALL_JS_URL,
                "notes": "Imported from Behr ColorSmart all.js dataset; LAB uses provided a/b/luminosity fields.",
            },
            "stockMatchable": True,
            "availabilityNotes": None,
            "aliases": [entry["friend"]] if entry.get("friend") else [],
            "catalogOrder": index,
            "active": None,
            "sourceConfidence": "high",
            "lastVerifiedAt": iso_now(),
            "regions": ["US"],
            "tags": [
                tag for tag, active in {
                    "basic": entry.get("isbasic") == "true",
                    "legacy": entry.get("islegacycolor") == "true",
                    "rack": entry.get("israck") == "true",
                    "rack-ultra": entry.get("israckultra") == "true",
                    "ultra": entry.get("isultra") == "true",
                }.items() if active
            ],
        }
        if entry.get("colorDescription"):
            record["source"]["notes"] += f" Description: {entry['colorDescription']}"
        catalog.append(record)

    write_json(CATALOG_DIR / "behr.json", catalog)
    return ImportSummary(
        manufacturer="Behr",
        raw_files=[str(raw_js_path.relative_to(ROOT)), str(raw_records_path.relative_to(ROOT))],
        record_count=len(catalog),
        notes=["Source is official first-party Behr ColorSmart JS payload."],
    )


def glidden_algolia_headers() -> dict[str, str]:
    return {
        "X-Algolia-API-Key": GLIDDEN_ALGOLIA_SEARCH_KEY,
        "X-Algolia-Application-Id": GLIDDEN_ALGOLIA_APP_ID,
        "Content-Type": "application/json",
    }


def fetch_glidden_algolia_page(page: int, hits_per_page: int = 1000) -> dict[str, Any]:
    url = f"https://{GLIDDEN_ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{GLIDDEN_ALGOLIA_INDEX}/query"
    payload = {"query": "", "hitsPerPage": hits_per_page, "page": page}
    return fetch_json(url, method="POST", headers=glidden_algolia_headers(), payload=payload)


def parse_glidden_detail(page_html: str) -> dict[str, str | None]:
    rgb_match = re.search(r'data-rgb="\s*([0-9\s,]+)\s*"', page_html)
    undertone_match = re.search(r'with\s+(?:an?\s+)?([^<\.]+?)\s+undertone', page_html, re.I)
    title_match = re.search(r'<title>(.*?)</title>', page_html, re.I | re.S)
    code_match = re.search(r'<div class="heading-style-h6">([^<]+)</div>', page_html, re.I)
    description_match = re.search(r'<div class="w-richtext"><p>(.*?)</p></div>', page_html, re.I | re.S)
    rgb = rgb_match.group(1).replace(" ", "") if rgb_match else None
    undertone = undertone_match.group(1).strip() if undertone_match else None
    return {
        "rgb": rgb,
        "undertone": undertone,
        "pageTitle": html.unescape(title_match.group(1).strip()) if title_match else None,
        "brandCode": html.unescape(code_match.group(1).strip()) if code_match else None,
        "description": html.unescape(re.sub(r'<[^>]+>', '', description_match.group(1)).strip()) if description_match else None,
    }


def import_glidden() -> ImportSummary:
    manufacturer = "glidden"
    raw_dir = RAW_DIR / manufacturer
    raw_dir.mkdir(parents=True, exist_ok=True)

    homepage = fetch_text(GLIDDEN_HOME_URL)
    homepage_path = raw_dir / "homepage.html"
    homepage_path.write_text(homepage)

    key_capture = {
        "fetchedAt": iso_now(),
        "homepageUrl": GLIDDEN_HOME_URL,
        "algoliaAppId": GLIDDEN_ALGOLIA_APP_ID,
        "algoliaSearchKey": GLIDDEN_ALGOLIA_SEARCH_KEY,
        "algoliaIndex": GLIDDEN_ALGOLIA_INDEX,
        "notes": "Values captured from inline search widget on official homepage.",
    }
    key_capture_path = raw_dir / "algolia-config.json"
    write_json(key_capture_path, key_capture)

    page0 = fetch_glidden_algolia_page(0)
    nb_pages = int(page0["nbPages"])
    page_paths: list[str] = []
    hits: list[dict[str, Any]] = []
    for page in range(nb_pages):
        data = page0 if page == 0 else fetch_glidden_algolia_page(page)
        page_path = raw_dir / f"algolia-page-{page}.json"
        write_json(page_path, data)
        page_paths.append(str(page_path.relative_to(ROOT)))
        hits.extend(data["hits"])

    sitemap_xml = fetch_text(GLIDDEN_SITEMAP_URL)
    sitemap_path = raw_dir / "sitemap.xml"
    sitemap_path.write_text(sitemap_xml)
    sitemap_urls = re.findall(r'<loc>(https://www\.glidden\.com/colors/[^<]+)</loc>', sitemap_xml)

    details: list[dict[str, Any]] = []
    for page_url in sitemap_urls:
        page_html = fetch_text(page_url)
        slug = page_url.rstrip("/").split("/")[-1]
        parsed = parse_glidden_detail(page_html)
        details.append({
            "page_url": page_url,
            "slug": slug,
            **parsed,
        })

    details_path = raw_dir / "details.parsed.json"
    write_json(details_path, {
        "fetchedAt": iso_now(),
        "count": len(details),
        "records": details,
    })
    detail_by_url = {item["page_url"]: item for item in details}
    hit_by_url = {item["page_url"]: item for item in hits}

    catalog: list[dict[str, Any]] = []
    missing_rgb: list[str] = []
    for index, page_url in enumerate(sitemap_urls, start=1):
        detail = detail_by_url.get(page_url, {})
        hit = hit_by_url.get(page_url, {})
        rgb = detail.get("rgb")
        brand_code = detail.get("brandCode") or hit.get("color_number")
        if not rgb or not brand_code:
            missing_rgb.append(page_url)
            continue
        hex_value = rgb_triplet_to_hex(rgb)
        r, g, b = [int(part) for part in rgb.split(",")]
        page_title = detail.get("pageTitle") or ''
        title_tail = page_title.replace(' Paint Color | Glidden', '').strip()
        title_code = None
        if brand_code and title_tail.endswith(brand_code):
            title_name = title_tail[: -len(brand_code)].strip()
            title_code = brand_code
        else:
            title_match = re.match(r'(.+?)\s+([^|]+?)\s+Paint Color \| Glidden$', page_title)
            title_name = title_match.group(1).strip() if title_match else title_tail
            title_code = title_match.group(2).strip() if title_match else None
        brand_code = html.unescape(brand_code or title_code or '').strip() or None
        display_name = html.unescape(hit.get("title") or title_name)
        notes = "Imported from official Glidden sitemap plus official color detail page RGB swatch data."
        if hit:
            notes += " Supplemental family/teaser metadata came from the official homepage-exposed Algolia search index."
        if detail.get("undertone"):
            notes += f" Undertone text parsed from detail description: {detail['undertone']}."
        record = {
            "id": sanitize_id("glidden", brand_code),
            "displayName": display_name,
            "manufacturer": "Glidden",
            "brand": "Glidden",
            "brandCode": brand_code,
            "libraryType": "native",
            "rgbHex": hex_value,
            "lab": rgb_to_lab(r, g, b),
            "source": {
                "kind": "official",
                "url": page_url,
                "notes": notes,
            },
            "stockMatchable": True,
            "availabilityNotes": None,
            "aliases": [],
            "catalogOrder": index,
            "active": None,
            "sourceConfidence": "high",
            "lastVerifiedAt": iso_now(),
            "regions": ["US"],
            "tags": [hit["color_family"]] if hit.get("color_family") else [],
        }
        catalog.append(record)

    write_json(CATALOG_DIR / "glidden.json", catalog)

    notes = [
        "Source uses official sitemap + detail pages, with official Algolia metadata as supplemental provenance.",
        f"Skipped {len(missing_rgb)} sitemap URLs with missing parsed RGB or brand code." if missing_rgb else "All sitemap color pages resolved to RGB detail data.",
        f"Sitemap listed {len(sitemap_urls)} color detail pages; Algolia index returned {len(hits)} color hits.",
    ]
    if missing_rgb:
        missing_path = raw_dir / "missing-rgb-urls.json"
        write_json(missing_path, missing_rgb)
        page_paths.append(str(missing_path.relative_to(ROOT)))

    return ImportSummary(
        manufacturer="Glidden",
        raw_files=[str(homepage_path.relative_to(ROOT)), str(key_capture_path.relative_to(ROOT)), str(sitemap_path.relative_to(ROOT)), *page_paths, str(details_path.relative_to(ROOT))],
        record_count=len(catalog),
        notes=notes,
    )


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text())


def validate_catalog(path: Path, schema: dict[str, Any]) -> list[str]:
    allowed_props = set(schema["properties"].keys())
    required = set(schema["required"])
    data = json.loads(path.read_text())
    errors: list[str] = []
    if not isinstance(data, list):
        return [f"{path.name}: expected top-level array"]
    for idx, item in enumerate(data):
        missing = required - set(item.keys())
        extra = set(item.keys()) - allowed_props
        if missing:
            errors.append(f"{path.name}[{idx}] missing required keys: {sorted(missing)}")
        if extra:
            errors.append(f"{path.name}[{idx}] unexpected keys: {sorted(extra)}")
        if "rgbHex" in item and not re.match(r"^#[0-9A-Fa-f]{6}$", item["rgbHex"]):
            errors.append(f"{path.name}[{idx}] invalid rgbHex: {item['rgbHex']}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Import official Behr and Glidden catalogs")
    parser.add_argument("manufacturer", choices=["behr", "glidden", "all"], nargs="?", default="all")
    args = parser.parse_args()

    ensure_dirs()
    summaries: list[ImportSummary] = []
    if args.manufacturer in {"behr", "all"}:
        summaries.append(import_behr())
    if args.manufacturer in {"glidden", "all"}:
        summaries.append(import_glidden())

    schema = load_schema()
    errors: list[str] = []
    for target in ["behr", "glidden"] if args.manufacturer == "all" else [args.manufacturer]:
        errors.extend(validate_catalog(CATALOG_DIR / f"{target}.json", schema))

    output = {
        "generatedAt": iso_now(),
        "summaries": [summary.__dict__ for summary in summaries],
        "validationErrors": errors,
    }
    print(json.dumps(output, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
