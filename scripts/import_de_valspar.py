#!/usr/bin/env python3
"""Import Dunn-Edwards and Valspar official/public catalogs.

Sources used:
- Dunn-Edwards: official download page, official ACO swatch file, official JPG swatch zip,
  and official Shopify all-colors JSON collection.
- Valspar: official browse-colors HTML wall markup.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CATALOG_DIR = ROOT / "data" / "catalogs"
USER_AGENT = "Mozilla/5.0 (compatible; paint-palette-tool/1.0)"

DUNN_DOWNLOAD_PAGE = "https://www.dunnedwards.com/colors/download-color-swatches/"
DUNN_ADOBE_ZIP = "https://www.dunnedwards.com/wp-content/uploads/2025/06/PerfectPalette2025_Adobe.zip"
DUNN_JPG_ZIP = "https://www.dunnedwards.com/wp-content/uploads/2025/06/Dunn-Edwards-JPG-Color-Library.zip"
DUNN_PRODUCTS_JSON = "https://shop.dunnedwards.com/collections/all-colors/products.json"
VALSPAR_URL = "https://www.valspar.com/en/colors/browse-colors"
VALSPAR_PRO_PAGES = {
    "color-toolkit": "https://www.valspar.com/en/professionals/color-toolkit",
    "interior-neutrals": "https://www.valspar.com/en/professionals/interior-neutrals",
    "exterior-color-combinations": "https://www.valspar.com/en/professionals/exterior-color-combinations",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", errors="replace")


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def hex_to_rgb(rgb_hex: str) -> Tuple[int, int, int]:
    rgb_hex = rgb_hex.lstrip("#")
    return tuple(int(rgb_hex[i : i + 2], 16) for i in (0, 2, 4))


def rgb_hex_to_lab(rgb_hex: str) -> Dict[str, float]:
    r8, g8, b8 = hex_to_rgb(rgb_hex)

    def srgb_to_linear(channel: float) -> float:
        channel = channel / 255.0
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    r = srgb_to_linear(r8)
    g = srgb_to_linear(g8)
    b = srgb_to_linear(b8)

    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

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
    return {"l": round((116 * fy) - 16, 3), "a": round(500 * (fx - fy), 3), "b": round(200 * (fy - fz), 3)}


def validate_record(record: Dict[str, object]) -> None:
    required = ["id", "displayName", "manufacturer", "brand", "brandCode", "libraryType", "rgbHex", "lab", "source"]
    for key in required:
        if key not in record:
            raise ValueError(f"missing required field {key}")
    if not re.match(r"^#[0-9A-F]{6}$", str(record["rgbHex"])):
        raise ValueError(f"bad rgbHex: {record['rgbHex']}")


def read_u16be(buf: bytes, offset: int) -> Tuple[int, int]:
    return struct.unpack_from(">H", buf, offset)[0], offset + 2


def dunn_split_name_code(name: str) -> Tuple[str, str]:
    name = re.sub(r"\s+", " ", name).strip()
    m = re.match(r"^(.*?)\s*\(((?:DE|DET|DEGR|DEFD|DEBN)\s*-?\s*[0-9A-Z]+)\)$", name, re.I)
    if m:
        return m.group(1).strip(), re.sub(r"\s+", "", m.group(2)).upper()
    m = re.match(r"^(.*?)\s+((?:DE|DET|DEGR|DEFD|DEBN)\s*-?\s*[0-9A-Z]+)$", name, re.I)
    if m:
        return m.group(1).strip(), re.sub(r"\s+", "", m.group(2)).upper()
    return name, name


def parse_aco_names_and_rgb(aco_bytes: bytes) -> List[Dict[str, str]]:
    offset = 0
    _v1, offset = read_u16be(aco_bytes, offset)
    count1, offset = read_u16be(aco_bytes, offset)
    offset += count1 * 10
    v2, offset = read_u16be(aco_bytes, offset)
    count2, offset = read_u16be(aco_bytes, offset)
    if v2 != 2:
        raise ValueError(f"Expected ACO v2 block, got {v2}")

    records = []
    for _ in range(count2):
        color_space, offset = read_u16be(aco_bytes, offset)
        w, offset = read_u16be(aco_bytes, offset)
        x, offset = read_u16be(aco_bytes, offset)
        y, offset = read_u16be(aco_bytes, offset)
        _z, offset = read_u16be(aco_bytes, offset)
        name_len = struct.unpack_from(">I", aco_bytes, offset)[0]
        offset += 4
        name_raw = aco_bytes[offset : offset + name_len * 2]
        offset += name_len * 2
        name = name_raw.decode("utf-16-be", errors="ignore").rstrip("\x00").strip()
        if color_space != 0:
            continue
        rgb_hex = f"#{round(w / 257):02X}{round(x / 257):02X}{round(y / 257):02X}"
        records.append({"name": name, "rgbHex": rgb_hex})
    return records


def fetch_dunn_shopify_products() -> List[dict]:
    page = 1
    per_page = 250
    products: List[dict] = []
    while True:
        url = f"{DUNN_PRODUCTS_JSON}?limit={per_page}&page={page}"
        chunk = json.loads(fetch_text(url)).get("products", [])
        products.extend(chunk)
        if len(chunk) < per_page:
            return products
        page += 1


def import_dunn_edwards() -> Dict[str, int]:
    raw_dir = RAW_DIR / "dunn-edwards"
    raw_dir.mkdir(parents=True, exist_ok=True)

    save_text(raw_dir / "download-page.html", fetch_text(DUNN_DOWNLOAD_PAGE))
    adobe_zip = fetch_bytes(DUNN_ADOBE_ZIP)
    jpg_zip = fetch_bytes(DUNN_JPG_ZIP)
    save_bytes(raw_dir / "PerfectPalette2025_Adobe.zip", adobe_zip)
    save_bytes(raw_dir / "Dunn-Edwards-JPG-Color-Library.zip", jpg_zip)

    with zipfile.ZipFile(raw_dir / "PerfectPalette2025_Adobe.zip") as zf:
        aco_name = next(name for name in zf.namelist() if name.lower().endswith(".aco"))
        aco_bytes = zf.read(aco_name)
    save_bytes(raw_dir / Path(aco_name).name, aco_bytes)
    aco_records = parse_aco_names_and_rgb(aco_bytes)

    products = fetch_dunn_shopify_products()
    save_json(raw_dir / "products.json", {
        "capturedAt": now_iso(),
        "source": DUNN_PRODUCTS_JSON,
        "productCount": len(products),
        "products": products,
    })

    products_by_code: Dict[str, dict] = {}
    for idx, product in enumerate(products, start=1):
        display_name, code = dunn_split_name_code(product["title"])
        if code == product["title"]:
            continue
        tags = product.get("tags", [])
        products_by_code[code] = {
            "displayName": display_name,
            "handle": product.get("handle"),
            "catalogOrder": idx,
            "families": sorted({tag.replace("Color Family_", "") for tag in tags if tag.startswith("Color Family_")}),
            "collections": sorted({tag.replace("Color Group_", "") for tag in tags if tag.startswith("Color Group_")}),
            "published": bool(product.get("published_at")),
        }

    normalized = []
    unmatched = []
    seen = set()
    for swatch in aco_records:
        display_name, code = dunn_split_name_code(swatch["name"])
        if code in seen:
            continue
        seen.add(code)
        product = products_by_code.get(code)
        if not product:
            unmatched.append({"acoName": swatch["name"], "brandCode": code, "rgbHex": swatch["rgbHex"]})
            continue
        record = {
            "id": f"dunn-edwards:{slugify(code)}",
            "displayName": product["displayName"] or display_name,
            "manufacturer": "Dunn-Edwards",
            "brand": "Dunn-Edwards",
            "brandCode": code,
            "libraryType": "native",
            "rgbHex": swatch["rgbHex"],
            "lab": rgb_hex_to_lab(swatch["rgbHex"]),
            "source": {
                "kind": "official",
                "url": f"https://shop.dunnedwards.com/products/{product['handle']}" if product.get("handle") else DUNN_DOWNLOAD_PAGE,
                "notes": "RGB came from the official downloadable ACO swatch file; handle and tag enrichment came from the official Shopify all-colors JSON collection.",
            },
            "stockMatchable": True,
            "availabilityNotes": "Official Dunn-Edwards digital swatch and shop catalog sources agree on this code.",
            "aliases": [swatch["name"]] if swatch["name"] != product["displayName"] else [],
            "catalogOrder": product["catalogOrder"],
            "active": product["published"],
            "sourceConfidence": "high",
            "lastVerifiedAt": now_iso(),
            "regions": ["US"],
            "tags": product["families"] + product["collections"],
        }
        validate_record(record)
        normalized.append(record)

    normalized.sort(key=lambda r: ((r["catalogOrder"] is None), r["catalogOrder"] or 0, r["brandCode"]))
    save_json(CATALOG_DIR / "dunn-edwards.json", normalized)
    save_json(raw_dir / "provenance.json", {
        "capturedAt": now_iso(),
        "sources": [DUNN_DOWNLOAD_PAGE, DUNN_ADOBE_ZIP, DUNN_JPG_ZIP, DUNN_PRODUCTS_JSON],
        "acoRecordCount": len(aco_records),
        "shopifyProductCount": len(products),
        "normalizedRecordCount": len(normalized),
        "unmatchedAcoSample": unmatched[:100],
        "notes": [
            "ACO file is the authoritative official digital swatch source for RGB values.",
            "Shopify all-colors JSON provides handles plus family/collection merchandising tags.",
            "ACO contained more colors than the current shop catalog; unmatched ACO colors were withheld from normalized output in this pass.",
        ],
    })
    return {"records": len(normalized), "aco": len(aco_records), "shopify": len(products), "unmatched": len(unmatched)}


def import_valspar() -> Dict[str, int]:
    raw_dir = RAW_DIR / "valspar"
    raw_dir.mkdir(parents=True, exist_ok=True)
    html = fetch_text(VALSPAR_URL)
    save_text(raw_dir / "browse-colors.html", html)

    pro_pages = {}
    for slug, url in VALSPAR_PRO_PAGES.items():
        page_html = fetch_text(url)
        save_text(raw_dir / f"{slug}.html", page_html)
        pro_pages[slug] = {"url": url, "html": page_html}

    pattern = re.compile(r'<div class="grid--wall__item grid--wall__item-product grid--wall__item-color[^"]*"(?P<attrs>[^>]*)>', re.I)

    def attr(attrs: str, name: str) -> Optional[str]:
        m = re.search(rf'{re.escape(name)}="([^"]*)"', attrs)
        return unescape(m.group(1)).strip() if m else None

    records = []
    seen_codes = set()
    for idx, match in enumerate(pattern.finditer(html), start=1):
        attrs = match.group("attrs")
        code = attr(attrs, "data-color-id")
        name = attr(attrs, "data-color-name")
        rgb_hex = attr(attrs, "data-hex")
        family = attr(attrs, "data-color-family")
        collection = attr(attrs, "data-color-collection")
        retailer = attr(attrs, "data-retailer")
        anchor_slice = html[match.start() : match.start() + 1500]
        href_match = re.search(r'<a class="color-anchor"[^>]*href="([^"]+)"', anchor_slice, re.I)
        href = urllib.parse.urljoin(VALSPAR_URL, unescape(href_match.group(1))) if href_match else None

        if not code or not name or not rgb_hex or code in seen_codes:
            continue
        seen_codes.add(code)
        rgb_hex = rgb_hex.upper()
        record = {
            "id": f"valspar:{slugify(code)}",
            "displayName": name,
            "manufacturer": "Valspar",
            "brand": "Valspar",
            "brandCode": code,
            "libraryType": "native",
            "rgbHex": rgb_hex,
            "lab": rgb_hex_to_lab(rgb_hex),
            "source": {
                "kind": "official",
                "url": href,
                "notes": "Parsed from official Valspar browse-colors HTML wall markup.",
            },
            "stockMatchable": True,
            "availabilityNotes": "Official Valspar browse-colors listing.",
            "aliases": [],
            "catalogOrder": idx,
            "active": True,
            "sourceConfidence": "high",
            "lastVerifiedAt": now_iso(),
            "regions": ["US"],
            "tags": [tag for tag in [family, collection, retailer] if tag],
        }
        validate_record(record)
        records.append(record)

    records_by_url = {record["source"]["url"]: record for record in records if record["source"].get("url")}
    records_by_code = {record["brandCode"]: record for record in records}
    palette_memberships = []
    palette_records = []

    for palette_order, (slug, payload) in enumerate(pro_pages.items(), start=1):
        page_html = payload["html"]
        page_url = payload["url"]
        title_match = re.search(r"<title>(.*?)</title>", page_html, re.I | re.S)
        page_title = unescape(title_match.group(1)).strip() if title_match else slug.replace("-", " ").title()
        hrefs = re.findall(r'href="(/en/colors/browse-colors/[^"]+)"', page_html, re.I)
        unique_hrefs = []
        seen_hrefs = set()
        for href in hrefs:
            absolute = urllib.parse.urljoin(page_url, unescape(href))
            if absolute in seen_hrefs:
                continue
            seen_hrefs.add(absolute)
            unique_hrefs.append(absolute)

        matched = 0
        unmatched = []
        for item_order, absolute in enumerate(unique_hrefs, start=1):
            base = records_by_url.get(absolute)
            code_match = re.search(r'([A-Z]\d{3}-\d+[A-Z]?|\d{4}-\d+[A-Z]?)$', absolute, re.I)
            code = code_match.group(1).upper() if code_match else None
            if not base and code:
                base = records_by_code.get(code)
            if not base:
                unmatched.append({"url": absolute, "brandCodeGuess": code})
                continue

            matched += 1
            palette_memberships.append({
                "paletteSlug": slug,
                "paletteTitle": page_title,
                "paletteUrl": page_url,
                "paletteOrder": palette_order,
                "order": item_order,
                "brandCode": base["brandCode"],
                "displayName": base["displayName"],
                "colorUrl": base["source"]["url"],
            })
            derived = {
                "id": f"valspar-professional:{slugify(slug + '-' + base['brandCode'])}",
                "displayName": base["displayName"],
                "manufacturer": base["manufacturer"],
                "brand": base["brand"],
                "brandCode": base["brandCode"],
                "libraryType": "derived",
                "rgbHex": base["rgbHex"],
                "lab": base["lab"],
                "source": {
                    "kind": "derived",
                    "url": page_url,
                    "notes": f"Derived from the official Valspar professional page '{slug}' by matching linked official browse-colors entries to the canonical Valspar catalog.",
                },
                "stockMatchable": bool(base.get("stockMatchable")),
                "availabilityNotes": f"Featured on the official Valspar professional curated page '{slug}'. Base color data comes from the official browse-colors catalog.",
                "aliases": [],
                "catalogOrder": item_order,
                "active": True,
                "sourceConfidence": "high",
                "lastVerifiedAt": now_iso(),
                "regions": base.get("regions", ["US"]),
                "tags": sorted(set(list(base.get("tags", [])) + ["professional-curated", slug, f"palette:{slug}"])),
            }
            validate_record(derived)
            palette_records.append(derived)

        pro_pages[slug] = {
            "url": page_url,
            "pageTitle": page_title,
            "linkedColorCount": len(unique_hrefs),
            "matchedColorCount": matched,
            "unmatched": unmatched,
            "paletteOrder": palette_order,
        }

    save_json(CATALOG_DIR / "valspar.json", records)
    save_json(CATALOG_DIR / "valspar-professional-curated.json", palette_records)
    save_json(raw_dir / "professional-palettes.parsed.json", {
        "capturedAt": now_iso(),
        "pages": pro_pages,
        "memberships": palette_memberships,
    })
    save_json(raw_dir / "provenance.json", {
        "capturedAt": now_iso(),
        "sourceUrl": VALSPAR_URL,
        "recordCount": len(records),
        "professionalPageCount": len(VALSPAR_PRO_PAGES),
        "professionalCuratedRecordCount": len(palette_records),
        "notes": [
            "All records were parsed from official Valspar browse-colors HTML attributes.",
            "Retailer/channel values were preserved in tags when present.",
            "No downloadable ASE/ACO/ZIP/PDF color library file was discovered on the official Valspar site in this pass.",
            "Official professional pages exposed curated color selections via links to browse-colors detail pages; those were captured separately as derived records and palette memberships.",
        ],
    })
    return {"records": len(records), "professional_curated_records": len(palette_records), "professional_pages": len(VALSPAR_PRO_PAGES)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["dunn-edwards", "valspar", "all"])
    args = parser.parse_args()
    results = {}
    if args.target in {"dunn-edwards", "all"}:
        results["dunn-edwards"] = import_dunn_edwards()
    if args.target in {"valspar", "all"}:
        results["valspar"] = import_valspar()
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
