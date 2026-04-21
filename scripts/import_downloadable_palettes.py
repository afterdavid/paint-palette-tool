#!/usr/bin/env python3
"""Capture and normalize official downloadable palette assets.

This pass focuses on official downloadable palette pages/assets for:
- Sherwin-Williams
- Benjamin Moore
- PPG

Important scope notes:
- These sources are palette/library downloads, not guaranteed full manufacturer catalogs.
- Normalized outputs are therefore written under data/catalogs/downloadable-palettes/
  so they stay clearly separate from canonical full-catalog files.
- PPG currently exposes official downloadable asset links on its page, but the linked
  Azure/Blob hosts were not DNS-resolvable from this environment during this pass.
  The importer preserves the official page capture and extracted asset manifest,
  but does not fabricate records when the binary palette files cannot be fetched.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "catalogs" / "downloadable-palettes"
USER_AGENT = "Mozilla/5.0 (compatible; paint-palette-tool/1.0; downloadable palette importer)"

SW_PAGE = "https://www.sherwin-williams.com/painting-contractors/color/color-tools/downloadable-color-palettes"
BM_PAGE = "https://www.benjaminmoore.com/en-us/architects-designers/download-benjamin-moore-color-palettes"
PPG_PAGE = "https://www.ppgpaints.com/designers/professional-color-tools/palette-downloads"


@dataclass
class ImportResult:
    manufacturer: str
    raw_assets: int = 0
    parsed_records: int = 0
    written_records: int = 0
    notes: str = ""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def save_bytes(path: Path, data: bytes) -> None:
    ensure_dir(path.parent)
    path.write_bytes(data)


def save_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_text(url: str, timeout: int = 90) -> str:
    return fetch(url, timeout=timeout).decode("utf-8", errors="replace")


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def rgb_hex_to_lab(rgb_hex: str) -> dict[str, float]:
    rgb_hex = rgb_hex.lstrip("#")
    r = int(rgb_hex[0:2], 16) / 255.0
    g = int(rgb_hex[2:4], 16) / 255.0
    b = int(rgb_hex[4:6], 16) / 255.0

    def srgb_to_linear(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

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
    return {
        "l": round(116 * fy - 16, 3),
        "a": round(500 * (fx - fy), 3),
        "b": round(200 * (fy - fz), 3),
    }


def parse_html_links(html: str, page_url: str) -> list[str]:
    links = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        links.append(urllib.parse.urljoin(page_url, href))
    return links


def read_u16be(buf: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from(">H", buf, offset)[0], offset + 2


def parse_aco_names_and_rgb(aco_bytes: bytes) -> list[dict[str, str]]:
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


def parse_ase(ase_bytes: bytes) -> list[dict[str, Any]]:
    if ase_bytes[:4] != b"ASEF":
        raise ValueError("Not an ASE file")
    block_count = struct.unpack(">I", ase_bytes[8:12])[0]
    offset = 12
    groups: list[str] = []
    entries: list[dict[str, Any]] = []

    for _ in range(block_count):
        block_type, block_len = struct.unpack(">HI", ase_bytes[offset : offset + 6])
        offset += 6
        block = ase_bytes[offset : offset + block_len]
        offset += block_len

        if block_type == 0xC001:
            if len(block) >= 2:
                name_len = struct.unpack(">H", block[:2])[0]
                raw = block[2 : 2 + name_len * 2]
                group_name = raw.decode("utf-16-be", errors="ignore").rstrip("\x00").strip()
                if group_name:
                    groups.append(group_name)
            continue
        if block_type == 0xC002:
            if groups:
                groups.pop()
            continue
        if block_type != 0x0001 or len(block) < 2:
            continue

        name_len = struct.unpack(">H", block[:2])[0]
        pos = 2
        raw_name = block[pos : pos + name_len * 2]
        pos += name_len * 2
        name = raw_name.decode("utf-16-be", errors="ignore").rstrip("\x00").strip()
        if pos + 4 > len(block):
            continue
        model = block[pos : pos + 4].decode("ascii", errors="ignore")
        pos += 4
        if model == "RGB ":
            if pos + 12 > len(block):
                continue
            r, g, b = struct.unpack(">fff", block[pos : pos + 12])
            rgb_hex = f"#{round(max(0, min(1, r)) * 255):02X}{round(max(0, min(1, g)) * 255):02X}{round(max(0, min(1, b)) * 255):02X}"
        elif model == "GRAY":
            if pos + 4 > len(block):
                continue
            gray = struct.unpack(">f", block[pos : pos + 4])[0]
            ch = round(max(0, min(1, gray)) * 255)
            rgb_hex = f"#{ch:02X}{ch:02X}{ch:02X}"
        else:
            continue
        entries.append({"name": name, "rgbHex": rgb_hex, "groups": list(groups), "model": model.strip()})
    return entries


def parse_bm_name(name: str) -> tuple[str, str]:
    name = re.sub(r"\s+", " ", name).strip()
    match = re.match(r"^([A-Z0-9\-]+)\s+(.+)$", name)
    if match:
        return match.group(2).strip(), match.group(1).strip()
    return name, name


def parse_sw_name(name: str) -> tuple[str, str]:
    name = re.sub(r"\s+", " ", name).strip()
    match = re.match(r"^(.*?)\s*\((SW\s*\d{4})\)$", name, re.I)
    if match:
        return match.group(1).strip(), re.sub(r"\s+", "", match.group(2)).upper()
    match = re.match(r"^(SW\s*\d{4})\s+(.+)$", name, re.I)
    if match:
        return match.group(2).strip(), re.sub(r"\s+", "", match.group(1)).upper()
    return name, name


def build_record(*, manufacturer: str, brand: str, display_name: str, brand_code: str, rgb_hex: str, source_url: str, note: str, palette_tags: list[str], aliases: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": f"{slugify(manufacturer)}:{slugify(brand_code)}",
        "displayName": display_name,
        "manufacturer": manufacturer,
        "brand": brand,
        "brandCode": brand_code,
        "libraryType": "native",
        "rgbHex": rgb_hex,
        "lab": rgb_hex_to_lab(rgb_hex),
        "source": {
            "kind": "official",
            "url": source_url,
            "notes": note,
        },
        "stockMatchable": True,
        "availabilityNotes": "Imported from official downloadable palette assets. These files represent downloadable library collections and may not equal complete brand catalog coverage.",
        "aliases": aliases or [],
        "catalogOrder": None,
        "active": None,
        "sourceConfidence": "high",
        "lastVerifiedAt": now_iso(),
        "regions": ["US"],
        "tags": palette_tags,
    }


def import_sherwin_williams() -> ImportResult:
    manufacturer = "sherwin-williams"
    raw_dir = RAW_DIR / manufacturer / "downloadable-palettes"
    ensure_dir(raw_dir)
    ensure_dir(OUT_DIR)

    html = fetch_text(SW_PAGE)
    save_text(raw_dir / "download-page.html", html)
    links = parse_html_links(html, SW_PAGE)

    asset_urls = OrderedDict([
        ("color-by-number-csp-ase", next(link for link in links if link.endswith("sw-colors-number-csp-ase.ase"))),
        ("color-by-number-ede-ase", next(link for link in links if link.endswith("sw-colors-number-ede-ase.ase"))),
        ("colorsnap-jpg-zip", next(link for link in links if link.endswith("sw-colorsnap-coll-by-number.zip"))),
        ("designer-jpg-zip", next(link for link in links if link.endswith("sw-ede-coll-by-number.zip"))),
    ])

    manifest = {"capturedAt": now_iso(), "pageUrl": SW_PAGE, "assets": []}
    merged: dict[str, dict[str, Any]] = {}
    palette_name_map = {
        "color-by-number-csp-ase": "palette:ColorSnap Collection",
        "color-by-number-ede-ase": "palette:Designer Color Collection",
    }

    for key, url in asset_urls.items():
        data = fetch(url)
        filename = Path(urllib.parse.urlparse(url).path).name
        save_bytes(raw_dir / filename, data)
        manifest["assets"].append({"key": key, "url": url, "filename": filename, "bytes": len(data)})
        if filename.lower().endswith(".ase"):
            for entry in parse_ase(data):
                display_name, brand_code = parse_sw_name(entry["name"])
                if not re.fullmatch(r"SW\d{4}", brand_code):
                    continue
                rec = merged.get(brand_code)
                tag = palette_name_map[key]
                if rec is None:
                    rec = build_record(
                        manufacturer="Sherwin-Williams",
                        brand="Sherwin-Williams",
                        display_name=display_name,
                        brand_code=brand_code,
                        rgb_hex=entry["rgbHex"],
                        source_url=url,
                        note="RGB/name imported from Sherwin-Williams official downloadable ASE palette assets.",
                        palette_tags=[tag],
                    )
                    merged[brand_code] = rec
                elif tag not in rec["tags"]:
                    rec["tags"].append(tag)

    records = sorted(merged.values(), key=lambda r: r["brandCode"])
    save_json(raw_dir / "manifest.json", manifest)
    save_json(OUT_DIR / "sherwin-williams.json", records)
    return ImportResult(manufacturer, raw_assets=len(manifest["assets"]), parsed_records=len(records), written_records=len(records), notes="Parsed official Sherwin-Williams ASE palette downloads (ColorSnap + Designer Color Collection).")


def import_benjamin_moore() -> ImportResult:
    manufacturer = "benjamin-moore"
    raw_dir = RAW_DIR / manufacturer / "downloadable-palettes"
    ensure_dir(raw_dir)
    ensure_dir(OUT_DIR)

    html = fetch_text(BM_PAGE)
    save_text(raw_dir / "download-page.html", html)
    links = parse_html_links(html, BM_PAGE)
    ase_urls = [link for link in links if link.lower().endswith(".ase")]
    unique_ase_urls = list(OrderedDict((url, None) for url in ase_urls).keys())

    manifest = {"capturedAt": now_iso(), "pageUrl": BM_PAGE, "assets": []}
    merged: dict[str, dict[str, Any]] = {}

    for url in unique_ase_urls:
        data = fetch(url)
        filename = Path(urllib.parse.urlparse(url).path).name
        save_bytes(raw_dir / filename, data)
        palette_label = filename.replace("benjaminmoore_", "").replace("_en-us.ase", "").replace("BenjaminMoore_", "").replace(".ase", "")
        palette_label = palette_label.replace("_", " ").strip()
        manifest["assets"].append({"url": url, "filename": filename, "bytes": len(data), "palette": palette_label})
        for entry in parse_ase(data):
            display_name, brand_code = parse_bm_name(entry["name"])
            if not brand_code:
                continue
            rec = merged.get(brand_code)
            tag = f"palette:{palette_label}"
            if rec is None:
                rec = build_record(
                    manufacturer="Benjamin Moore",
                    brand="Benjamin Moore",
                    display_name=display_name,
                    brand_code=brand_code,
                    rgb_hex=entry["rgbHex"],
                    source_url=url,
                    note="RGB/name imported from Benjamin Moore official downloadable ASE palette assets.",
                    palette_tags=[tag],
                )
                merged[brand_code] = rec
            else:
                if tag not in rec["tags"]:
                    rec["tags"].append(tag)
                if rec["displayName"] == rec["brandCode"] and display_name != brand_code:
                    rec["displayName"] = display_name

    records = sorted(merged.values(), key=lambda r: r["brandCode"])
    save_json(raw_dir / "manifest.json", manifest)
    save_json(OUT_DIR / "benjamin-moore.json", records)
    return ImportResult(manufacturer, raw_assets=len(manifest["assets"]), parsed_records=len(records), written_records=len(records), notes="Parsed official Benjamin Moore ASE palette downloads across downloadable design collections.")


def import_ppg() -> ImportResult:
    manufacturer = "ppg"
    raw_dir = RAW_DIR / manufacturer / "downloadable-palettes"
    ensure_dir(raw_dir)
    ensure_dir(OUT_DIR)

    html = fetch_text(PPG_PAGE)
    save_text(raw_dir / "download-page.html", html)
    links = parse_html_links(html, PPG_PAGE)

    wanted = []
    for link in links:
        lower = link.lower()
        if any(token in lower for token in ["voc-colornumber-2022.aco", "voc-colornumber-2022.ase", "rgb-and-lrv-values.xlsx"]):
            wanted.append(link)
    wanted = list(OrderedDict((url, None) for url in wanted).keys())

    manifest = {"capturedAt": now_iso(), "pageUrl": PPG_PAGE, "assets": []}
    for url in wanted:
        filename = Path(urllib.parse.urlparse(url).path).name or "download"
        item: dict[str, Any] = {"url": url, "filename": filename}
        try:
            data = fetch(url)
            save_bytes(raw_dir / filename, data)
            item.update({"status": "downloaded", "bytes": len(data)})
            if filename.lower().endswith(".aco"):
                item["acoColorCount"] = len(parse_aco_names_and_rgb(data))
            elif filename.lower().endswith(".ase"):
                item["aseColorCount"] = len(parse_ase(data))
        except Exception as exc:
            item.update({"status": "error", "error": str(exc)})
        manifest["assets"].append(item)

    save_json(raw_dir / "manifest.json", manifest)
    note = "Captured official PPG downloadable palette page and extracted asset URLs, but linked binary palette/data files were not retrievable from this environment during this pass (DNS resolution failures on the linked Azure/Blob hosts). No normalized color records were written."
    return ImportResult(manufacturer, raw_assets=len(manifest["assets"]), parsed_records=0, written_records=0, notes=note)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manufacturer", choices=["sherwin-williams", "benjamin-moore", "ppg", "all"])
    args = parser.parse_args()

    results: list[ImportResult] = []
    if args.manufacturer in {"sherwin-williams", "all"}:
        results.append(import_sherwin_williams())
    if args.manufacturer in {"benjamin-moore", "all"}:
        results.append(import_benjamin_moore())
    if args.manufacturer in {"ppg", "all"}:
        results.append(import_ppg())

    for result in results:
        print(
            f"{result.manufacturer}: raw_assets={result.raw_assets} parsed={result.parsed_records} "
            f"written={result.written_records} notes={result.notes}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
