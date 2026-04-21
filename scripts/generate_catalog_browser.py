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
    'white', 'neutral', 'gray', 'black',
    'blue', 'teal', 'green', 'yellow', 'orange', 'red', 'pink', 'purple',
    'brown', 'beige', 'tan', 'unknown'
]

KEYWORDS = [
    ('white', ['white', 'snow', 'ivory', 'cream', 'cotton', 'frost', 'pearl']),
    ('neutral', ['neutral', 'linen', 'taupe', 'greige', 'stone', 'mushroom', 'putty', 'oat', 'oyster']),
    ('gray', ['gray', 'grey', 'silver', 'slate', 'charcoal', 'graphite', 'ash', 'smoke']),
    ('black', ['black', 'noir', 'onyx', 'caviar', 'ink', 'night', 'midnight']),
    ('blue', ['blue', 'navy', 'sky', 'ocean', 'cerulean', 'indigo', 'cobalt', 'azure']),
    ('teal', ['teal', 'turquoise', 'aqua', 'cyan']),
    ('green', ['green', 'sage', 'olive', 'moss', 'forest', 'mint', 'lime', 'eucalyptus']),
    ('yellow', ['yellow', 'gold', 'amber', 'butter', 'lemon', 'sun']),
    ('orange', ['orange', 'apricot', 'peach', 'coral', 'terracotta']),
    ('red', ['red', 'crimson', 'scarlet', 'brick', 'rust', 'burgundy', 'maroon']),
    ('pink', ['pink', 'rose', 'blush']),
    ('purple', ['purple', 'violet', 'plum', 'lavender', 'lilac']),
    ('brown', ['brown', 'umber', 'mocha', 'espresso', 'coffee', 'chocolate', 'walnut', 'cedar']),
    ('beige', ['beige', 'sand', 'biscuit', 'almond']),
    ('tan', ['tan', 'khaki', 'camel', 'buff', 'suede']),
]


def hex_to_rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hsl(h: str):
    r, g, b = [x / 255.0 for x in hex_to_rgb(h)]
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        hue = sat = 0.0
    else:
        d = mx - mn
        sat = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            hue = (g - b) / d + (6 if g < b else 0)
        elif mx == g:
            hue = (b - r) / d + 2
        else:
            hue = (r - g) / d + 4
        hue /= 6
    return hue, sat, l


def family_for(rec):
    text = ' '.join([
        str(rec.get('displayName', '')),
        str(rec.get('brand', '')),
        str(rec.get('brandCode', '')),
        ' '.join(rec.get('tags', []) if isinstance(rec.get('tags'), list) else [])
    ]).lower()
    for family, words in KEYWORDS:
        if any(w in text for w in words):
            return family
    h = rec.get('rgbHex') or '#808080'
    r, g, b = hex_to_rgb(h)
    if max(r, g, b) < 35:
        return 'black'
    if min(r, g, b) > 235:
        return 'white'
    return 'unknown'


def perceptual_sort_key(rgb_hex: str, family: str):
    hue, sat, light = rgb_to_hsl(rgb_hex)
    # Main goal: light to dark. Secondary: family-appropriate hue/saturation ordering.
    if family in {'white', 'neutral', 'gray', 'black', 'beige', 'tan', 'brown'}:
        return (-light, sat, hue)
    return (-light, hue, -sat)


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
            rec = dict(rec)
            rec['_source_file'] = p.name
            rec['_family'] = family_for(rec)
            rec['_sort'] = perceptual_sort_key(rgb, rec['_family'])
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
                rec = dict(rec)
                rec['_source_file'] = f'downloadable-palettes/{p.name}'
                rec['_family'] = family_for(rec)
                rec['_sort'] = perceptual_sort_key(rgb, rec['_family'])
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
            tooltip = esc(f"{title}\n{brand} {code}\n{rgb}\n{source}")
            tiles.append(
                f'<button class="tile" style="background:{rgb}" '
                f'data-name="{title}" data-brand="{brand}" data-code="{code}" '
                f'data-hex="{rgb}" data-source="{source}" title="{tooltip}"></button>'
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
.layout {{ display:grid; grid-template-columns: 250px 1fr 280px; min-height:100vh; }}
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
<p>Unmerged swatches from the imported catalogs. Each family is shown as a dense visual field, sorted to read more like paint chips than database cards.</p>
{nav}
</nav>
<main>
<header>
<h1>Every Color We Have So Far</h1>
<p>Grouped by color family, then arranged perceptually: mostly light to dark, with hue and saturation used to keep nearby colors visually coherent. Hover or click a swatch for details.</p>
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
<div class="detail-row"><strong>Source:</strong> <span id="detail-source">—</span></div>
<p class="helper">This page is intentionally unmerged. It is for visually inspecting range and density before we decide how aggressively to collapse near-duplicates into a working palette.</p>
</aside>
</div>
<script>
const els = {{
  swatch: document.getElementById('detail-swatch'),
  name: document.getElementById('detail-name'),
  brand: document.getElementById('detail-brand'),
  code: document.getElementById('detail-code'),
  hex: document.getElementById('detail-hex'),
  source: document.getElementById('detail-source'),
}};
function setDetail(tile) {{
  els.swatch.style.background = tile.style.background;
  els.name.textContent = tile.dataset.name || 'Untitled';
  els.brand.textContent = tile.dataset.brand || 'Unknown';
  els.code.textContent = tile.dataset.code || '—';
  els.hex.textContent = tile.dataset.hex || '—';
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
