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
    if L >= 94 and C <= 8:
        return 'white'
    if L <= 22 and C <= 10:
        return 'black'
    if C <= 12:
        return 'neutral'
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


def remap_family(L: float, C: float, h: float, family: str):
    if family in {'red', 'orange', 'yellow'} and L < 55 and C < 35:
        return 'brown'
    return family


def normalize(v: float, lo: float, hi: float):
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (v - lo) / (hi - lo)))


def tile_position(family: str, L: float, C: float, h: float):
    # Return x, y in [0,1] for 2D placement.
    # y always reads top(light) -> bottom(dark)
    y = 1.0 - normalize(L, 0, 100)

    if family == 'neutral':
        # cool -> warm using a/b balance
        x = normalize(a_warmcool(L, C, h), -1, 1)
        return x, y
    if family == 'white':
        x = normalize(C, 0, 12)
        return x, y
    if family == 'black':
        x = normalize(C, 0, 16)
        return x, y
    if family == 'brown':
        # keep earthy hues left->right with chroma as subtle spread
        x = normalize(h if h <= 90 else 45, 20, 60)
        x = (x * 0.8) + (normalize(C, 0, 60) * 0.2)
        return x, y
    # chromatic families: hue across, chroma adds slight spread
    family_ranges = {
        'red': (345, 380),
        'orange': (20, 45),
        'yellow': (45, 75),
        'green': (75, 160),
        'teal': (160, 190),
        'blue': (190, 270),
        'purple': (270, 320),
        'pink': (320, 345),
        'unknown': (0, 360),
    }
    lo, hi = family_ranges.get(family, (0, 360))
    hue_val = h
    if family == 'red' and h < 40:
        hue_val = h + 360
    x = normalize(hue_val, lo, hi)
    # Compress very low chroma colors toward center so they don't stray too much.
    chroma_bias = (normalize(C, 0, 80) - 0.5) * 0.18
    x = max(0.0, min(1.0, x + chroma_bias))
    return x, y


def a_warmcool(L: float, C: float, h: float):
    # neutrals: approximate warm/cool axis using hue around blue vs yellow/red sides
    if C <= 1:
        return 0.0
    radians = math.radians(h)
    return math.cos(radians)


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
            L, C, h = lab_to_lch(L, a, b)
            family = remap_family(L, C, h, family_for_lch(L, C, h))
            x, y = tile_position(family, L, C, h)
            rec = dict(rec)
            rec['_source_file'] = p.name
            rec['_family'] = family
            rec['_lch'] = (L, C, h)
            rec['_pos'] = (x, y)
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
                L, C, h = lab_to_lch(L, a, b)
                family = remap_family(L, C, h, family_for_lch(L, C, h))
                x, y = tile_position(family, L, C, h)
                rec = dict(rec)
                rec['_source_file'] = f'downloadable-palettes/{p.name}'
                rec['_family'] = family
                rec['_lch'] = (L, C, h)
                rec['_pos'] = (x, y)
                items.append(rec)
    return items


def esc(s: str) -> str:
    return (str(s)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;'))


def make_tiles_for_family(recs):
    cols = 28
    rows = 18
    buckets = [[None for _ in range(cols)] for _ in range(rows)]
    overflow = []

    def place(rec):
        x, y = rec['_pos']
        c = min(cols - 1, max(0, int(round(x * (cols - 1)))))
        r = min(rows - 1, max(0, int(round(y * (rows - 1)))))
        # Spiral-ish nearest-open search
        best = None
        for radius in range(0, max(cols, rows)):
            for rr in range(max(0, r - radius), min(rows, r + radius + 1)):
                for cc in range(max(0, c - radius), min(cols, c + radius + 1)):
                    if buckets[rr][cc] is None:
                        dist = abs(rr - r) + abs(cc - c)
                        cand = (dist, rr, cc)
                        if best is None or cand < best:
                            best = cand
            if best is not None:
                _, rr, cc = best
                buckets[rr][cc] = rec
                return
        overflow.append(rec)

    for rec in sorted(recs, key=lambda r: (r['_pos'][1], r['_pos'][0], -r['_lch'][1])):
        place(rec)

    html = []
    for r in range(rows):
        for c in range(cols):
            rec = buckets[r][c]
            if rec is None:
                html.append('<div class="cell empty"></div>')
                continue
            rgb = rec.get('rgbHex') or rec.get('rgb') or rec.get('hex')
            title = esc(rec.get('displayName') or rec.get('name') or 'Untitled')
            brand = esc(rec.get('brand') or rec.get('manufacturer') or 'Unknown')
            code = esc(rec.get('brandCode') or '')
            source = esc(rec.get('_source_file', ''))
            L, C, h = rec['_lch']
            tooltip = esc(f"{title}\n{brand} {code}\n{rgb}\nLCH: {L:.1f}, {C:.1f}, {h:.1f}\n{source}")
            html.append(
                f'<button class="cell tile" style="background:{rgb}" '
                f'data-name="{title}" data-brand="{brand}" data-code="{code}" '
                f'data-hex="{rgb}" data-source="{source}" '
                f'data-lch="L {L:.1f} · C {C:.1f} · H {h:.1f}" '
                f'title="{tooltip}"></button>'
            )
    if overflow:
        for rec in overflow:
            rgb = rec.get('rgbHex') or rec.get('rgb') or rec.get('hex')
            title = esc(rec.get('displayName') or rec.get('name') or 'Untitled')
            brand = esc(rec.get('brand') or rec.get('manufacturer') or 'Unknown')
            code = esc(rec.get('brandCode') or '')
            source = esc(rec.get('_source_file', ''))
            L, C, h = rec['_lch']
            tooltip = esc(f"{title}\n{brand} {code}\n{rgb}\nLCH: {L:.1f}, {C:.1f}, {h:.1f}\n{source}")
            html.append(
                f'<button class="cell tile overflow" style="background:{rgb}" '
                f'data-name="{title}" data-brand="{brand}" data-code="{code}" '
                f'data-hex="{rgb}" data-source="{source}" '
                f'data-lch="L {L:.1f} · C {C:.1f} · H {h:.1f}" '
                f'title="{tooltip}"></button>'
            )
    return ''.join(html), rows, cols, len(overflow)


def main():
    items = load_catalogs()
    grouped = {k: [] for k in COLOR_ORDER}
    for rec in items:
        fam = rec['_family'] if rec['_family'] in grouped else 'unknown'
        grouped.setdefault(fam, []).append(rec)

    nav = '\n'.join(
        f'<a href="#{fam}">{fam.title()} <span>{len(grouped.get(fam, []))}</span></a>'
        for fam in COLOR_ORDER if grouped.get(fam)
    )

    sections = []
    for fam in COLOR_ORDER:
        recs = grouped.get(fam, [])
        if not recs:
            continue
        tiles_html, rows, cols, overflow = make_tiles_for_family(recs)
        note = f' · {overflow} overflow' if overflow else ''
        sections.append(
            f'<section id="{fam}"><h2>{fam.title()} <span>{len(recs)} colors{note}</span></h2>'
            f'<div class="map-wrap"><div class="axis axis-top">hue / warm-cool drift →</div>'
            f'<div class="axis axis-left">light → dark</div>'
            f'<div class="swatch-map" style="grid-template-columns: repeat({cols}, 1fr);">{tiles_html}</div></div></section>'
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
.map-wrap {{ position:relative; padding-left:26px; padding-top:18px; }}
.axis {{ color:var(--muted); font-size:11px; letter-spacing:.02em; }}
.axis-top {{ margin:0 0 8px 0; }}
.axis-left {{ position:absolute; left:0; top:42px; writing-mode:vertical-rl; transform: rotate(180deg); }}
.swatch-map {{ display:grid; gap:4px; align-items:stretch; }}
.cell {{ width:100%; aspect-ratio:1 / 1; border-radius:4px; }}
.tile {{ appearance:none; border:none; cursor:pointer; box-shadow: inset 0 0 0 1px rgba(255,255,255,.10); transition: transform .05s ease, box-shadow .05s ease; }}
.tile:hover, .tile:focus {{ transform: scale(1.1); position:relative; z-index:1; box-shadow: inset 0 0 0 1px rgba(255,255,255,.55), 0 0 0 2px rgba(255,255,255,.12); }}
.empty {{ background: transparent; }}
.overflow {{ outline: 1px dashed rgba(255,255,255,.18); }}
aside {{ position:sticky; top:0; height:100vh; overflow:auto; padding:20px; background:var(--panel); border-left:1px solid var(--line); }}
.panel-title {{ margin:0 0 12px; font-size:16px; }}
.detail-swatch {{ width:100%; aspect-ratio: 1.6 / 1; border-radius:12px; background:#444; border:1px solid rgba(255,255,255,.14); margin-bottom:14px; }}
.detail-name {{ font-size:18px; font-weight:700; margin-bottom:6px; line-height:1.25; }}
.detail-row {{ color:var(--muted); font-size:13px; line-height:1.45; margin-bottom:6px; word-break:break-word; }}
.detail-row strong {{ color:var(--text); font-weight:600; }}
.helper {{ color:var(--muted); font-size:13px; line-height:1.45; }}
.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
#mobile-sheet {{ display:none; }}
@media (max-width: 1100px) {{ .layout {{ grid-template-columns: 240px 1fr; }} aside {{ display:none; }} }}
@media (max-width: 900px) {{
  .layout {{ grid-template-columns: 1fr; }}
  nav {{ position:relative; height:auto; border-right:none; border-bottom:1px solid var(--line); }}
  main {{ padding:18px; }}
  .swatch-map {{ gap:3px; }}
  .map-wrap {{ padding-left:18px; padding-top:16px; }}
  .axis-left {{ top:36px; font-size:10px; }}
  #mobile-sheet {{ display:block; position:fixed; left:0; right:0; bottom:0; z-index:20; background:rgba(21,25,30,.98); border-top:1px solid var(--line); padding:14px 16px calc(14px + env(safe-area-inset-bottom)); transform:translateY(100%); transition:transform .18s ease; backdrop-filter: blur(8px); }}
  #mobile-sheet.open {{ transform:translateY(0); }}
  .sheet-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }}
  .sheet-close {{ appearance:none; border:none; background:var(--panel2); color:var(--text); border-radius:999px; padding:8px 12px; font-size:12px; }}
  .sheet-swatch {{ width:64px; height:64px; border-radius:10px; border:1px solid rgba(255,255,255,.12); margin-bottom:10px; }}
}}
</style>
</head>
<body>
<div class="layout">
<nav>
<h1>Catalog Browser</h1>
<p>Unmerged swatches from the imported catalogs. Families and positions are now derived from LAB/LCH-style color math, then placed into a real 2D map instead of a row-by-row sorted grid.</p>
{nav}
</nav>
<main>
<header>
<h1>Every Color We Have So Far</h1>
<p>Each family is now shown as a 2D color field. Lightness runs top to bottom, and horizontal drift follows hue or warm/cool logic depending on the family. On mobile, tap a swatch to open details.</p>
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
<p class="helper">This page is still unmerged. The goal now is to make the visual field itself coherent before we decide how aggressively to collapse near-duplicates into a working palette.</p>
</aside>
</div>
<div id="mobile-sheet">
  <div class="sheet-head"><strong>Swatch details</strong><button id="sheet-close" class="sheet-close">Close</button></div>
  <div id="sheet-swatch" class="sheet-swatch"></div>
  <div class="detail-row"><strong>Name:</strong> <span id="m-name">—</span></div>
  <div class="detail-row"><strong>Brand:</strong> <span id="m-brand">—</span></div>
  <div class="detail-row"><strong>Code:</strong> <span id="m-code">—</span></div>
  <div class="detail-row"><strong>Hex:</strong> <span id="m-hex" class="mono">—</span></div>
  <div class="detail-row"><strong>LCH:</strong> <span id="m-lch" class="mono">—</span></div>
  <div class="detail-row"><strong>Source:</strong> <span id="m-source">—</span></div>
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
const mobile = {{
  sheet: document.getElementById('mobile-sheet'),
  close: document.getElementById('sheet-close'),
  swatch: document.getElementById('sheet-swatch'),
  name: document.getElementById('m-name'),
  brand: document.getElementById('m-brand'),
  code: document.getElementById('m-code'),
  hex: document.getElementById('m-hex'),
  lch: document.getElementById('m-lch'),
  source: document.getElementById('m-source'),
}};
function setDetail(tile) {{
  els.swatch.style.background = tile.style.background;
  els.name.textContent = tile.dataset.name || 'Untitled';
  els.brand.textContent = tile.dataset.brand || 'Unknown';
  els.code.textContent = tile.dataset.code || '—';
  els.hex.textContent = tile.dataset.hex || '—';
  els.lch.textContent = tile.dataset.lch || '—';
  els.source.textContent = tile.dataset.source || '—';
  mobile.swatch.style.background = tile.style.background;
  mobile.name.textContent = tile.dataset.name || 'Untitled';
  mobile.brand.textContent = tile.dataset.brand || 'Unknown';
  mobile.code.textContent = tile.dataset.code || '—';
  mobile.hex.textContent = tile.dataset.hex || '—';
  mobile.lch.textContent = tile.dataset.lch || '—';
  mobile.source.textContent = tile.dataset.source || '—';
}}
document.querySelectorAll('.tile').forEach(tile => {{
  tile.addEventListener('mouseenter', () => setDetail(tile));
  tile.addEventListener('focus', () => setDetail(tile));
  tile.addEventListener('click', () => {{
    setDetail(tile);
    if (window.innerWidth <= 900) mobile.sheet.classList.add('open');
  }});
}});
mobile.close?.addEventListener('click', () => mobile.sheet.classList.remove('open'));
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
