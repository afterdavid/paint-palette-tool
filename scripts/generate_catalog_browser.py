#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path('/Users/theo/apps/paint-palette-tool')
CATALOG_DIR = ROOT / 'data' / 'catalogs'
OUT = ROOT / 'output' / 'catalog-browser.html'
DOCS = ROOT / 'docs' / 'index.html'

COLOR_ORDER = [
    'white', 'neutral', 'black',
    'red', 'orange', 'yellow', 'green', 'teal', 'blue', 'purple', 'pink',
    'brown', 'unknown'
]


def hex_to_rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def srgb_channel_to_linear(c: float) -> float:
    c = c / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def rgb_to_xyz(rgb_hex: str):
    r8, g8, b8 = hex_to_rgb(rgb_hex)
    r = srgb_channel_to_linear(r8)
    g = srgb_channel_to_linear(g8)
    b = srgb_channel_to_linear(b8)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    return x, y, z


def xyz_to_lab(x: float, y: float, z: float):
    # D65 reference white
    xr = x / 0.95047
    yr = y / 1.00000
    zr = z / 1.08883

    def f(t: float) -> float:
        d = 6 / 29
        if t > d ** 3:
            return t ** (1 / 3)
        return t / (3 * d * d) + 4 / 29

    fx = f(xr)
    fy = f(yr)
    fz = f(zr)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return L, a, b


def rgb_to_lab(rgb_hex: str):
    return xyz_to_lab(*rgb_to_xyz(rgb_hex))


def lab_to_lch(L: float, a: float, b: float):
    C = math.sqrt(a * a + b * b)
    h = math.degrees(math.atan2(b, a))
    if h < 0:
        h += 360
    return L, C, h


def family_for_lch(L: float, C: float, h: float):
    # Achromatic buckets first
    if L >= 94 and C <= 8:
        return 'white'
    if L <= 22 and C <= 10:
        return 'black'
    if C <= 12:
        return 'neutral'

    # Chromatic buckets by hue angle
    if h < 20 or h >= 345:
        return 'red'
    if h < 45:
        return 'orange'
    if h < 75:
        return 'yellow'
    if h < 160:
        return 'green'
    if h < 190:
        return 'teal'
    if h < 270:
        return 'blue'
    if h < 320:
        return 'purple'
    if h < 345:
        return 'pink'
    return 'unknown'


def sort_key_for_lch(family: str, L: float, C: float, h: float):
    # Light to dark first everywhere.
    if family == 'neutral':
        # Keep neutrals lined up mostly by lightness, then warm/cool, then chroma.
        warm_cool = a_warm_cool_from_hue(h)
        return (-L, warm_cool, C)
    if family in {'white', 'black'}:
        return (-L, C, h)
    if family == 'brown':
        return (-L, C, h)
    return (-L, h, -C)


def a_warm_cool_from_hue(h: float):
    # lower = cooler, higher = warmer; rough helper for neutral ordering
    if 200 <= h <= 340:
        return 0
    return 1


def load_catalogs():
    items = []
    for p in sorted(CATALOG_DIR.glob('*.json')):
        if p.name in {'paint-store-accessible.json'}:
            continue
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for rec in data:
            if not isinstance(rec, dict):
                continue
            rgb = rec.get('rgbHex') or rec.get('rgb') or rec.get('hex')
            if not isinstance(rgb, str) or not rgb.startswith('#') or len(rgb) != 7:
                continue
            L, a, b = rgb_to_lab(rgb)
            _, C, h = lab_to_lch(L, a, b)
            family = family_for_lch(L, C, h)
            # Push dark, low-chroma warm colors into brown instead of red/orange when appropriate.
            if family in {'red', 'orange', 'yellow'} and L < 55 and C < 35:
                family = 'brown'
            rec = dict(rec)
            rec['_source_file'] = p.name
            rec['_family'] = family
            rec['_lab'] = (L, a, b)
            rec['_lch'] = (L, C, h)
            rec['_sort'] = sort_key_for_lch(family, L, C, h)
            items.append(rec)
    dlp = CATALOG_DIR / 'downloadable-palettes'
    if dlp.exists():
        for p in sorted(dlp.glob('*.json')):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            for rec in data:
                if not isinstance(rec, dict):
                    continue
                rgb = rec.get('rgbHex') or rec.get('rgb') or rec.get('hex')
                if not isinstance(rgb, str) or not rgb.startswith('#') or len(rgb) != 7:
                    continue
                L, a, b = rgb_to_lab(rgb)
                _, C, h = lab_to_lch(L, a, b)
                family = family_for_lch(L, C, h)
                if family in {'red', 'orange', 'yellow'} and L < 55 and C < 35:
                    family = 'brown'
                rec = dict(rec)
                rec['_source_file'] = f'downloadable-palettes/{p.name}'
                rec['_family'] = family
                rec['_lab'] = (L, a, b)
                rec['_lch'] = (L, C, h)
                rec['_sort'] = sort_key_for_lch(family, L, C, h)
                items.append(rec)
    return items


def esc(s: str) -> str:
    return (str(s)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;'))


def main():
    items = load_catalogs()
    grouped = {k: [] for k in COLOR_ORDER}
    for rec in items:
        fam = rec['_family'] if rec['_family'] in grouped else 'unknown'
        grouped.setdefault(fam, []).append(rec)
    for fam in grouped:
        grouped[fam].sort(key=lambda r: r['_sort'])

    nav = '\n'.join(
        f'<a href="#{fam}">{fam.title()} <span>{len(grouped.get(fam, []))}</span></a>'
        for fam in COLOR_ORDER if grouped.get(fam)
    )

    sections = []
    for fam in COLOR_ORDER:
        recs = grouped.get(fam, [])
        if not recs:
            continue
        tiles = []
        for r in recs:
            rgb = r.get('rgbHex') or r.get('rgb') or r.get('hex')
            title = esc(r.get('displayName') or r.get('name') or 'Untitled')
            brand = esc(r.get('brand') or r.get('manufacturer') or 'Unknown')
            code = esc(r.get('brandCode') or '')
            source = esc(r.get('_source_file', ''))
            L, C, h = r['_lch']
            tooltip = esc(f"{title}\n{brand} {code}\n{rgb}\nLCH: {L:.1f}, {C:.1f}, {h:.1f}\n{source}")
            tiles.append(
                f'<button class="tile" style="background:{rgb}" '
                f'data-name="{title}" data-brand="{brand}" data-code="{code}" '
                f'data-hex="{rgb}" data-source="{source}" '
                f'data-lch="L {L:.1f} · C {C:.1f} · H {h:.1f}" '
                f'title="{tooltip}"></button>'
            )
        sections.append(
            f'<section id="{fam}"><h2>{fam.title()} <span>{len(recs)} colors</span></h2>'
            f'<div class="swatch-grid">{"".join(tiles)}</div></section>'
        )

    html = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Paint Palette Tool – Catalog Browser</title>
<style>
:root {{ --bg:#0f1114; --panel:#15191e; --panel2:#1b2027; --text:#eef2f7; --muted:#9aa6b2; --line:#2a3139; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; background:var(--bg); color:var(--text); }}
.layout {{ display:grid; grid-template-columns: 250px 1fr 300px; min-height:100vh; }}
nav {{ position:sticky; top:0; height:100vh; overflow:auto; padding:20px; background:var(--panel); border-right:1px solid var(--line); }}
nav h1 {{ font-size:16px; margin:0 0 10px; }}
nav p {{ color:var(--muted); font-size:13px; line-height:1.45; }}
nav a {{ display:flex; justify-content:space-between; gap:12px; padding:8px 10px; border-radius:8px; color:var(--text); text-decoration:none; font-size:14px; }}
nav a:hover {{ background:var(--panel2); }}
main {{ padding:24px; }}
header {{ margin-bottom:20px; }}
header h1 {{ margin:0 0 8px; font-size:28px; }}
header p {{ margin:0; color:var(--muted); max-width:800px; line-height:1.5; }}
section {{ margin-bottom:36px; }}
section h2 {{ position:sticky; top:0; z-index:2; background:linear-gradient(to bottom, rgba(15,17,20,.98), rgba(15,17,20,.88)); backdrop-filter: blur(6px); margin:0 0 12px; padding:10px 0; font-size:20px; border-bottom:1px solid var(--line); }}
section h2 span {{ color:var(--muted); font-size:14px; margin-left:8px; font-weight:400; }}
.swatch-grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(24px, 1fr)); gap:4px; align-items:stretch; }}
.tile {{ appearance:none; border:none; width:100%; aspect-ratio:1 / 1; border-radius:4px; cursor:pointer; box-shadow: inset 0 0 0 1px rgba(255,255,255,.10); transition: transform .05s ease, box-shadow .05s ease; }}
.tile:hover, .tile:focus {{ transform: scale(1.1); position:relative; z-index:1; box-shadow: inset 0 0 0 1px rgba(255,255,255,.55), 0 0 0 2px rgba(255,255,255,.12); }}
aside {{ position:sticky; top:0; height:100vh; overflow:auto; padding:20px; background:var(--panel); border-left:1px solid var(--line); }}
.panel-title {{ margin:0 0 12px; font-size:16px; }}
.detail-swatch {{ width:100%; aspect-ratio: 1.6 / 1; border-radius:12px; background:#444; border:1px solid rgba(255,255,255,.14); margin-bottom:14px; }}
.detail-name {{ font-size:18px; font-weight:700; margin-bottom:6px; line-height:1.25; }}
.detail-row {{ color:var(--muted); font-size:13px; line-height:1.45; margin-bottom:6px; word-break:break-word; }}
.detail-row strong {{ color:var(--text); font-weight:600; }}
.helper {{ color:var(--muted); font-size:13px; line-height:1.45; }}
.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
@media (max-width: 1100px) {{ .layout {{ grid-template-columns: 240px 1fr; }} aside {{ display:none; }} }}
@media (max-width: 900px) {{ .layout {{ grid-template-columns: 1fr; }} nav {{ position:relative; height:auto; border-right:none; border-bottom:1px solid var(--line); }} main {{ padding:18px; }} .swatch-grid {{ grid-template-columns: repeat(auto-fill, minmax(22px, 1fr)); }} }}
</style>
</head>
<body>
<div class="layout">
<nav>
<h1>Catalog Browser</h1>
<p>Unmerged swatches from the imported catalogs. Families and ordering are now based on LAB/LCH-style color math instead of name heuristics.</p>
{nav}
</nav>
<main>
<header>
<h1>Every Color We Have So Far</h1>
<p>Grouped by perceptual color family using LCH-style thresholds. Within each family, swatches are arranged primarily light-to-dark, then by hue/chroma logic so the page behaves more like a real color field.</p>
</header>
{''.join(sections)}
</main>
<aside>
<h2 class="panel-title">Swatch details</h2>
<div id="detail-swatch" class="detail-swatch"></div>
<div id="detail-name" class="detail-name">Hover a swatch</div>
<div class="detail-row"><strong>Brand:</strong> <span id="detail-brand">—</span></div>
<div class="detail-row"><strong>Code:</strong> <span id="detail-code">—</span></div>
<div class="detail-row"><strong>Hex:</strong> <span id="detail-hex" class="mono">—</span></div>
<div class="detail-row"><strong>LCH:</strong> <span id="detail-lch" class="mono">—</span></div>
<div class="detail-row"><strong>Source:</strong> <span id="detail-source">—</span></div>
<p class="helper">This page is still unmerged. It is now arranged by perceptual math so we can see which colors are genuinely stragglers versus just badly sorted.</p>
</aside>
</div>
<script>
const els = {{
  swatch: document.getElementById('detail-swatch'),
  name: document.getElementById('detail-name'),
  brand: document.getElementById('detail-brand'),
  code: document.getElementById('detail-code'),
  hex: document.getElementById('detail-hex'),
  lch: document.getElementById('detail-lch'),
  source: document.getElementById('detail-source'),
}};
function setDetail(tile) {{
  els.swatch.style.background = tile.style.background;
  els.name.textContent = tile.dataset.name || 'Untitled';
  els.brand.textContent = tile.dataset.brand || 'Unknown';
  els.code.textContent = tile.dataset.code || '—';
  els.hex.textContent = tile.dataset.hex || '—';
  els.lch.textContent = tile.dataset.lch || '—';
  els.source.textContent = tile.dataset.source || '—';
}}
document.querySelectorAll('.tile').forEach(tile => {{
  tile.addEventListener('mouseenter', () => setDetail(tile));
  tile.addEventListener('focus', () => setDetail(tile));
  tile.addEventListener('click', () => setDetail(tile));
}});
</script>
</body>
</html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding='utf-8')
    DOCS.parent.mkdir(parents=True, exist_ok=True)
    DOCS.write_text(html, encoding='utf-8')
    print(f'Wrote {OUT}')
    print(f'Wrote {DOCS}')

if __name__ == '__main__':
    main()
