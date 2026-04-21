#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path('/Users/theo/apps/paint-palette-tool')
CATALOG_DIR = ROOT / 'data' / 'catalogs'
OUT = ROOT / 'output' / 'catalog-browser.html'

COLOR_ORDER = [
    'white', 'neutral', 'gray', 'black',
    'blue', 'green', 'yellow', 'orange', 'red', 'pink', 'purple',
    'brown', 'beige', 'tan', 'teal', 'unknown'
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


def rgb_to_hsl_sort(h: str):
    r, g, b = [x / 255.0 for x in hex_to_rgb(h)]
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        h2 = s = 0.0
    else:
        d = mx - mn
        s = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h2 = (g - b) / d + (6 if g < b else 0)
        elif mx == g:
            h2 = (b - r) / d + 2
        else:
            h2 = (r - g) / d + 4
        h2 /= 6
    return (round(h2, 4), round(s, 4), round(l, 4))


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
            rec['_sort'] = rgb_to_hsl_sort(rgb)
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
                rec['_sort'] = rgb_to_hsl_sort(rgb)
                items.append(rec)
    return items


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
        cards = []
        for r in recs:
            rgb = r.get('rgbHex') or r.get('rgb') or r.get('hex')
            title = r.get('displayName') or r.get('name') or 'Untitled'
            brand = r.get('brand') or r.get('manufacturer') or 'Unknown'
            code = r.get('brandCode') or ''
            source = r.get('_source_file', '')
            cards.append(f'''<div class="card"><div class="swatch" style="background:{rgb}"></div><div class="meta"><div class="title">{title}</div><div class="sub">{brand} {code}</div><div class="sub mono">{rgb}</div><div class="sub tiny">{source}</div></div></div>''')
        sections.append(f'''<section id="{fam}"><h2>{fam.title()} <span>{len(recs)} colors</span></h2><div class="grid">{''.join(cards)}</div></section>''')

    html = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Paint Palette Tool – Catalog Browser</title>
<style>
:root {{ --bg:#111315; --panel:#181b1f; --panel2:#20242a; --text:#f2f4f8; --muted:#aab3bf; --line:#2a3038; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; background:var(--bg); color:var(--text); }}
.layout {{ display:grid; grid-template-columns: 250px 1fr; min-height:100vh; }}
nav {{ position:sticky; top:0; height:100vh; overflow:auto; padding:20px; background:var(--panel); border-right:1px solid var(--line); }}
nav h1 {{ font-size:16px; margin:0 0 10px; }}
nav p {{ color:var(--muted); font-size:13px; line-height:1.4; }}
nav a {{ display:flex; justify-content:space-between; gap:12px; padding:8px 10px; border-radius:8px; color:var(--text); text-decoration:none; font-size:14px; }}
nav a:hover {{ background:var(--panel2); }}
main {{ padding:24px; }}
header {{ margin-bottom:24px; }}
header h1 {{ margin:0 0 8px; font-size:28px; }}
header p {{ margin:0; color:var(--muted); max-width:780px; line-height:1.5; }}
section {{ margin-bottom:40px; }}
section h2 {{ position:sticky; top:0; background:linear-gradient(to bottom, rgba(17,19,21,.98), rgba(17,19,21,.88)); backdrop-filter: blur(4px); margin:0 0 16px; padding:10px 0; font-size:20px; border-bottom:1px solid var(--line); }}
section h2 span {{ color:var(--muted); font-size:14px; margin-left:8px; font-weight:400; }}
.grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap:12px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
.swatch {{ height:92px; border-bottom:1px solid rgba(255,255,255,.06); }}
.meta {{ padding:10px; }}
.title {{ font-size:13px; font-weight:600; line-height:1.25; margin-bottom:6px; }}
.sub {{ font-size:12px; color:var(--muted); line-height:1.35; }}
.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
.tiny {{ font-size:11px; opacity:.8; margin-top:4px; }}
@media (max-width: 900px) {{ .layout {{ grid-template-columns: 1fr; }} nav {{ position:relative; height:auto; border-right:none; border-bottom:1px solid var(--line); }} }}
</style>
</head>
<body>
<div class="layout">
<nav>
<h1>Catalog Browser</h1>
<p>Unmerged swatches from the current imported catalogs. Grouped heuristically by color family so you can browse ranges visually.</p>
{nav}
</nav>
<main>
<header>
<h1>Every Color We Have So Far</h1>
<p>This is a first-pass visual browser from the currently imported JSON catalogs. Nothing here is merged. It is meant for browsing ranges, spotting density, and seeing where we have too many near-duplicates or holes.</p>
</header>
{''.join(sections)}
</main>
</div>
</body>
</html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding='utf-8')
    print(f'Wrote {OUT}')

if __name__ == '__main__':
    main()
