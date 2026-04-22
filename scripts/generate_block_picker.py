#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path('/Users/theo/apps/paint-palette-tool')
CATALOG_DIR = ROOT / 'data' / 'catalogs'
OUT = ROOT / 'docs' / 'prototypes' / 'block-picker.html'


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


def load_records():
    records = []
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
            records.append({
                'name': rec.get('displayName') or rec.get('name') or 'Untitled',
                'brand': rec.get('brand') or rec.get('manufacturer') or 'Unknown',
                'code': rec.get('brandCode') or '',
                'hex': rgb,
                'source': p.name,
                'L': L,
                'C': C,
                'H': h,
            })
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
                records.append({
                    'name': rec.get('displayName') or rec.get('name') or 'Untitled',
                    'brand': rec.get('brand') or rec.get('manufacturer') or 'Unknown',
                    'code': rec.get('brandCode') or '',
                    'hex': rgb,
                    'source': f'downloadable-palettes/{p.name}',
                    'L': L,
                    'C': C,
                    'H': h,
                })
    return records


def main():
    records = load_records()
    html = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Paint Palette Tool – Block Picker Prototype</title>
<style>
:root {{ --bg:#0f1114; --panel:#15191e; --panel2:#1b2027; --text:#eef2f7; --muted:#9aa6b2; --line:#2a3139; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; background:var(--bg); color:var(--text); }}
main {{ max-width:1200px; margin:0 auto; padding:24px; }}
header h1 {{ margin:0 0 8px; font-size:30px; }}
header p {{ color:var(--muted); line-height:1.5; max-width:860px; }}
.layout {{ display:grid; grid-template-columns: minmax(0, 1fr) 340px; gap:24px; align-items:start; }}
.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:16px; }}
.controls {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom:14px; }}
.controls label {{ display:block; font-size:12px; color:var(--muted); margin-bottom:6px; }}
.controls input {{ width:100%; }}
#grid {{ display:grid; grid-template-columns: repeat(32, 1fr); gap:2px; background:var(--bg); border-radius:12px; overflow:hidden; }}
.cell {{ aspect-ratio:1 / 1; border:none; cursor:pointer; padding:0; }}
.cell:hover, .cell:focus {{ outline:2px solid rgba(255,255,255,.55); outline-offset:-2px; position:relative; z-index:1; }}
.preview {{ width:100%; aspect-ratio: 1.6 / 1; border-radius:14px; border:1px solid rgba(255,255,255,.10); margin-top:14px; }}
.readout {{ margin-top:12px; color:var(--muted); font-size:13px; line-height:1.5; }}
.readout strong {{ color:var(--text); }}
.matches {{ display:grid; gap:10px; margin-top:14px; }}
.match {{ display:grid; grid-template-columns: 40px 1fr; gap:10px; align-items:center; background:var(--panel2); border:1px solid var(--line); border-radius:12px; padding:10px; }}
.match-swatch {{ width:40px; height:40px; border-radius:10px; }}
.match-name {{ font-size:13px; font-weight:700; }}
.match-meta {{ font-size:12px; color:var(--muted); line-height:1.35; }}
@media (max-width: 900px) {{ .layout {{ grid-template-columns: 1fr; }} .controls {{ grid-template-columns: 1fr; }} #grid {{ grid-template-columns: repeat(20, 1fr); }} }}
</style>
</head>
<body>
<main>
<header>
<h1>Block Picker Prototype</h1>
<p>This prototype uses only real imported manufacturer colors. No fake in-between colors are generated. Instead, the field is filled with mathematically arranged color blocks so every click is already a real paint color.</p>
</header>
<div class="layout">
  <section class="panel">
    <div class="controls">
      <div><label for="hueCenter">Hue center</label><input id="hueCenter" type="range" min="0" max="360" value="0" /></div>
      <div><label for="lightnessCenter">Lightness center</label><input id="lightnessCenter" type="range" min="0" max="100" value="60" /></div>
      <div><label for="windowSize">Window size</label><input id="windowSize" type="range" min="20" max="180" value="90" /></div>
    </div>
    <div id="grid"></div>
  </section>
  <aside class="panel">
    <div class="label">Selected real paint color</div>
    <div id="preview" class="preview"></div>
    <div id="readout" class="readout"></div>
    <div class="label" style="margin-top:16px;">Closest neighbors in current window</div>
    <div id="matches" class="matches"></div>
  </aside>
</div>
</main>
<script>
const RECORDS = {json.dumps(records)};
const hueCenter = document.getElementById('hueCenter');
const lightnessCenter = document.getElementById('lightnessCenter');
const windowSize = document.getElementById('windowSize');
const grid = document.getElementById('grid');
const preview = document.getElementById('preview');
const readout = document.getElementById('readout');
const matchesEl = document.getElementById('matches');
let currentSelection = null;

function circularDelta(a, b) {{
  const d = Math.abs(a - b);
  return Math.min(d, 360 - d);
}}

function score(rec, hc, lc) {{
  const hueDist = circularDelta(rec.H, hc);
  const lightDist = Math.abs(rec.L - lc);
  const chromaPenalty = Math.max(0, 8 - rec.C) * 0.5;
  return hueDist * 1.3 + lightDist * 1.0 + chromaPenalty;
}}

function render() {{
  const hc = parseFloat(hueCenter.value);
  const lc = parseFloat(lightnessCenter.value);
  const win = parseFloat(windowSize.value);
  const candidates = RECORDS
    .map(r => ({{...r, s: score(r, hc, lc)}}))
    .filter(r => r.s <= win)
    .sort((a,b) => a.s - b.s)
    .slice(0, 512);

  const sorted = candidates.sort((a,b) => {{
    const la = Math.round(a.L / 5), lb = Math.round(b.L / 5);
    if (lb !== la) return lb - la;
    return a.H - b.H || b.C - a.C;
  }});

  grid.innerHTML = sorted.map((r, idx) => `
    <button class="cell" style="background:${{r.hex}}" data-idx="${{idx}}" title="${{r.name}} · ${{r.brand}} ${{r.code}} · ${{r.hex}}"></button>
  `).join('');

  if (!currentSelection || !sorted.includes(currentSelection)) currentSelection = sorted[0] || null;
  updateDetail(sorted);

  [...grid.querySelectorAll('.cell')].forEach((el, idx) => {{
    el.addEventListener('click', () => {{
      currentSelection = sorted[idx];
      updateDetail(sorted);
    }});
  }});
}}

function updateDetail(sorted) {{
  const r = currentSelection;
  if (!r) {{
    preview.style.background = 'transparent';
    readout.innerHTML = '<div>No colors in current window.</div>';
    matchesEl.innerHTML = '';
    return;
  }}
  preview.style.background = r.hex;
  readout.innerHTML = `
    <div><strong>${{r.name}}</strong></div>
    <div>${{r.brand}} ${{r.code}}</div>
    <div>${{r.hex}}</div>
    <div>L ${{r.L.toFixed(1)}} · C ${{r.C.toFixed(1)}} · H ${{r.H.toFixed(1)}}</div>
    <div>${{r.source}}</div>
  `;
  const neighbors = sorted
    .map(n => ({{...n, d: Math.abs(n.L-r.L) + circularDelta(n.H,r.H) + Math.abs(n.C-r.C)}}))
    .sort((a,b) => a.d - b.d)
    .slice(0, 12);
  matchesEl.innerHTML = neighbors.map(n => `
    <div class="match">
      <div class="match-swatch" style="background:${{n.hex}}"></div>
      <div>
        <div class="match-name">${{n.name}}</div>
        <div class="match-meta">${{n.brand}} ${{n.code}} · ${{n.hex}} · d≈${{n.d.toFixed(1)}}</div>
      </div>
    </div>
  `).join('');
}}

[hueCenter, lightnessCenter, windowSize].forEach(el => el.addEventListener('input', render));
render();
</script>
</body>
</html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding='utf-8')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
