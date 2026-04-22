#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path('/Users/theo/apps/paint-palette-tool')
CATALOG_DIR = ROOT / 'data' / 'catalogs'
OUT = ROOT / 'output' / 'catalog-browser.html'
DOCS = ROOT / 'docs' / 'index.html'


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
            rec = dict(rec)
            rec['_source_file'] = p.name
            rec['_lch'] = (L, C, h)
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
                rec = dict(rec)
                rec['_source_file'] = f'downloadable-palettes/{p.name}'
                rec['_lch'] = (L, C, h)
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

    # lightness bands so the page stays navigable
    bands = [
        ('L90-100', 90, 100),
        ('L80-90', 80, 90),
        ('L70-80', 70, 80),
        ('L60-70', 60, 70),
        ('L50-60', 50, 60),
        ('L40-50', 40, 50),
        ('L30-40', 30, 40),
        ('L20-30', 20, 30),
        ('L0-20', 0, 20),
    ]

    nav = '\n'.join(
        f'<a href="#{slug}">{slug} <span>{sum(1 for r in items if lo <= r["_lch"][0] < hi or (hi == 100 and lo <= r["_lch"][0] <= hi))}</span></a>'
        for slug, lo, hi in bands
    )

    sections = []
    for slug, lo, hi in bands:
        recs = [r for r in items if (lo <= r['_lch'][0] < hi) or (hi == 100 and lo <= r['_lch'][0] <= hi)]
        # sort for deterministic rendering / layering
        recs.sort(key=lambda r: (r['_lch'][2], r['_lch'][1], -r['_lch'][0]))
        pts = []
        for r in recs:
            rgb = r.get('rgbHex') or r.get('rgb') or r.get('hex')
            title = esc(r.get('displayName') or r.get('name') or 'Untitled')
            brand = esc(r.get('brand') or r.get('manufacturer') or 'Unknown')
            code = esc(r.get('brandCode') or '')
            source = esc(r.get('_source_file', ''))
            L, C, h = r['_lch']
            angle = math.radians(h - 90)
            radius = min(1.0, C / 120.0)
            x = 50 + math.cos(angle) * radius * 46
            y = 50 + math.sin(angle) * radius * 46
            size = 10 if C > 10 else 8
            tooltip = esc(f"{title}\n{brand} {code}\n{rgb}\nLCH: {L:.1f}, {C:.1f}, {h:.1f}\n{source}")
            pts.append(
                f'<button class="dot" style="left:{x:.2f}%; top:{y:.2f}%; background:{rgb}; width:{size}px; height:{size}px;" '
                f'data-name="{title}" data-brand="{brand}" data-code="{code}" data-hex="{rgb}" '
                f'data-lch="L {L:.1f} · C {C:.1f} · H {h:.1f}" data-source="{source}" title="{tooltip}"></button>'
            )
        sections.append(
            f'<section id="{slug}"><h2>{slug} <span>{len(recs)} colors</span></h2>'
            f'<div class="wheel-wrap"><div class="wheel-axis axis-top">yellow / green</div><div class="wheel-axis axis-right">red</div><div class="wheel-axis axis-bottom">blue / purple</div><div class="wheel-axis axis-left">cyan</div><div class="wheel">{"".join(pts)}</div></div></section>'
        )

    html = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Paint Palette Tool – Radial LCH Browser</title>
<style>
:root {{ --bg:#0f1114; --panel:#15191e; --panel2:#1b2027; --text:#eef2f7; --muted:#9aa6b2; --line:#2a3139; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; background:var(--bg); color:var(--text); }}
.layout {{ display:grid; grid-template-columns: 240px 1fr 300px; min-height:100vh; }}
nav {{ position:sticky; top:0; height:100vh; overflow:auto; padding:20px; background:var(--panel); border-right:1px solid var(--line); }}
nav h1 {{ font-size:16px; margin:0 0 10px; }}
nav p {{ color:var(--muted); font-size:13px; line-height:1.45; }}
nav a {{ display:flex; justify-content:space-between; gap:12px; padding:8px 10px; border-radius:8px; color:var(--text); text-decoration:none; font-size:14px; }}
nav a:hover {{ background:var(--panel2); }}
main {{ padding:24px; }}
header {{ margin-bottom:22px; }}
header h1 {{ margin:0 0 8px; font-size:28px; }}
header p {{ margin:0; color:var(--muted); max-width:820px; line-height:1.5; }}
section {{ margin-bottom:40px; }}
section h2 {{ margin:0 0 14px; padding-bottom:10px; font-size:20px; border-bottom:1px solid var(--line); }}
section h2 span {{ color:var(--muted); font-size:14px; margin-left:8px; font-weight:400; }}
.wheel-wrap {{ position:relative; max-width:760px; aspect-ratio:1 / 1; margin:0 auto; }}
.wheel {{ position:absolute; inset:20px; border-radius:50%; border:1px solid rgba(255,255,255,.12); background:radial-gradient(circle at center, rgba(255,255,255,.03), rgba(255,255,255,.01) 45%, rgba(255,255,255,.00) 60%); }}
.wheel::before, .wheel::after {{ content:''; position:absolute; inset:50% auto auto 0; width:100%; height:1px; background:rgba(255,255,255,.06); transform:translateY(-50%); }}
.wheel::after {{ inset:0 auto auto 50%; width:1px; height:100%; transform:translateX(-50%); }}
.dot {{ position:absolute; transform:translate(-50%, -50%); border:none; border-radius:999px; cursor:pointer; box-shadow: inset 0 0 0 1px rgba(255,255,255,.25); }}
.dot:hover, .dot:focus {{ z-index:2; box-shadow: inset 0 0 0 1px rgba(255,255,255,.8), 0 0 0 3px rgba(255,255,255,.10); }}
.wheel-axis {{ position:absolute; color:var(--muted); font-size:12px; }}
.axis-top {{ top:0; left:50%; transform:translateX(-50%); }}
.axis-right {{ right:0; top:50%; transform:translateY(-50%); }}
.axis-bottom {{ bottom:0; left:50%; transform:translateX(-50%); }}
.axis-left {{ left:0; top:50%; transform:translateY(-50%); }}
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
  .wheel-wrap {{ max-width:100%; }}
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
<h1>Radial LCH Browser</h1>
<p>Experimental radial view. Each section is a lightness slice. Angle = hue, radius = chroma. This should make the overall color-space structure easier to understand than the family-by-family grids.</p>
{nav}
</nav>
<main>
<header>
<h1>Every Color We Have So Far</h1>
<p>This version uses a radial LCH-style view: hue around the circle, chroma out from the center, and lightness split into separate bands. Tap or click a swatch for details.</p>
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
<p class="helper">This is an exploratory view. It may not be the final picker, but it should reveal whether the space itself feels more coherent when shown as hue around a wheel and chroma as radial distance.</p>
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
document.querySelectorAll('.dot').forEach(tile => {{
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
