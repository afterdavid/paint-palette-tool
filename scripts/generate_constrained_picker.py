#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path('/Users/theo/apps/paint-palette-tool')
CATALOG_DIR = ROOT / 'data' / 'catalogs'
OUT = ROOT / 'docs' / 'prototypes' / 'constrained-picker.html'


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
            records.append({
                'name': rec.get('displayName') or rec.get('name') or 'Untitled',
                'brand': rec.get('brand') or rec.get('manufacturer') or 'Unknown',
                'code': rec.get('brandCode') or '',
                'hex': rgb,
                'source': p.name,
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
                records.append({
                    'name': rec.get('displayName') or rec.get('name') or 'Untitled',
                    'brand': rec.get('brand') or rec.get('manufacturer') or 'Unknown',
                    'code': rec.get('brandCode') or '',
                    'hex': rgb,
                    'source': f'downloadable-palettes/{p.name}',
                })
    return records


HTML_TEMPLATE = '''<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Paint Palette Tool – Constrained Picker Prototype</title>
<style>
:root { --bg:#0f1114; --panel:#15191e; --panel2:#1b2027; --text:#eef2f7; --muted:#9aa6b2; --line:#2a3139; }
* { box-sizing:border-box; }
body { margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; background:var(--bg); color:var(--text); }
main { max-width:1100px; margin:0 auto; padding:24px; }
header h1 { margin:0 0 8px; font-size:30px; }
header p { color:var(--muted); line-height:1.5; max-width:820px; }
.layout { display:grid; grid-template-columns: minmax(0, 1fr) 320px; gap:24px; align-items:start; }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:16px; }
.field-wrap { display:grid; grid-template-columns: minmax(0, 1fr) 28px; gap:12px; align-items:stretch; }
#field { width:100%; aspect-ratio:1 / 1; border-radius:14px; cursor:crosshair; display:block; }
#hue { width:28px; height:100%; min-height:280px; border-radius:999px; cursor:ns-resize; display:block; }
.label { font-size:12px; color:var(--muted); margin-bottom:8px; }
.preview { width:100%; aspect-ratio: 1.6 / 1; border-radius:14px; border:1px solid rgba(255,255,255,.10); margin-top:14px; }
.readout { margin-top:12px; color:var(--muted); font-size:13px; line-height:1.5; }
.readout strong { color:var(--text); }
.matches { display:grid; gap:10px; margin-top:14px; }
.match { display:grid; grid-template-columns: 40px 1fr; gap:10px; align-items:center; background:var(--panel2); border:1px solid var(--line); border-radius:12px; padding:10px; }
.match-swatch { width:40px; height:40px; border-radius:10px; }
.match-name { font-size:13px; font-weight:700; }
.match-meta { font-size:12px; color:var(--muted); line-height:1.35; }
.controls { display:grid; gap:14px; margin-bottom:14px; }
.range-row label { display:block; font-size:12px; color:var(--muted); margin-bottom:6px; }
.range-row input { width:100%; }
@media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<main>
<header>
<h1>Constrained Picker Prototype</h1>
<p>This prototype shifts from “browse every swatch” to “pick a target color smoothly, then map it to real paint colors.” The field feels Photoshop-like, while the catalog underneath constrains the match results to actual imported manufacturer colors.</p>
</header>
<div class="layout">
  <section class="panel">
    <div class="controls">
      <div class="range-row">
        <label for="lightnessBias">Lightness range focus</label>
        <input id="lightnessBias" type="range" min="0" max="100" value="55" />
      </div>
    </div>
    <div class="field-wrap">
      <div>
        <div class="label">Color field</div>
        <canvas id="field" width="700" height="700"></canvas>
      </div>
      <div>
        <div class="label">Hue</div>
        <canvas id="hue" width="28" height="700"></canvas>
      </div>
    </div>
  </section>
  <aside class="panel">
    <div class="label">Target preview</div>
    <div id="preview" class="preview"></div>
    <div id="readout" class="readout"></div>
    <div class="label" style="margin-top:16px;">Nearest imported paint colors</div>
    <div id="matches" class="matches"></div>
  </aside>
</div>
</main>
<script>
const RECORDS = __RECORDS_JSON__;

function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)];
}
function rgbToHex(r, g, b) {
  return '#' + [r,g,b].map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');
}
function hsvToRgb(h, s, v) {
  let c = v * s;
  let x = c * (1 - Math.abs((h / 60) % 2 - 1));
  let m = v - c;
  let r=0,g=0,b=0;
  if (h < 60) [r,g,b] = [c,x,0];
  else if (h < 120) [r,g,b] = [x,c,0];
  else if (h < 180) [r,g,b] = [0,c,x];
  else if (h < 240) [r,g,b] = [0,x,c];
  else if (h < 300) [r,g,b] = [x,0,c];
  else [r,g,b] = [c,0,x];
  return [255*(r+m),255*(g+m),255*(b+m)];
}
function rgbToXyz(rgb) {
  function lin(c) { c/=255; return c <= 0.04045 ? c/12.92 : Math.pow((c+0.055)/1.055, 2.4); }
  const [r8,g8,b8] = rgb;
  const r=lin(r8), g=lin(g8), b=lin(b8);
  return [
    r*0.4124564 + g*0.3575761 + b*0.1804375,
    r*0.2126729 + g*0.7151522 + b*0.0721750,
    r*0.0193339 + g*0.1191920 + b*0.9503041,
  ];
}
function xyzToLab(xyz) {
  const [x,y,z] = xyz;
  const xr=x/0.95047, yr=y/1.0, zr=z/1.08883;
  function f(t) { const d = 6/29; return t > d*d*d ? Math.cbrt(t) : t/(3*d*d)+4/29; }
  const fx=f(xr), fy=f(yr), fz=f(zr);
  return [116*fy-16, 500*(fx-fy), 200*(fy-fz)];
}
function rgbToLab(rgb) { return xyzToLab(rgbToXyz(rgb)); }
function labDistance(a, b) {
  return Math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2);
}

const enriched = RECORDS.map(r => ({ ...r, rgb: hexToRgb(r.hex), lab: rgbToLab(hexToRgb(r.hex)) }));
const field = document.getElementById('field');
const hueCanvas = document.getElementById('hue');
const preview = document.getElementById('preview');
const readout = document.getElementById('readout');
const matchesEl = document.getElementById('matches');
const lightnessBias = document.getElementById('lightnessBias');
const fctx = field.getContext('2d');
const hctx = hueCanvas.getContext('2d');
let hue = 0;
let sat = 0.8;
let val = 0.8;

function drawHue() {
  const h = hueCanvas.height;
  const grad = hctx.createLinearGradient(0, 0, 0, h);
  for (let i = 0; i <= 360; i += 60) grad.addColorStop(i/360, `hsl(${i}, 100%, 50%)`);
  hctx.clearRect(0,0,hueCanvas.width,h);
  hctx.fillStyle = grad;
  hctx.fillRect(0,0,hueCanvas.width,h);
  const y = (hue/360)*h;
  hctx.strokeStyle = 'white';
  hctx.lineWidth = 2;
  hctx.strokeRect(1, y-3, hueCanvas.width-2, 6);
}
function drawField() {
  const w = field.width, h = field.height;
  const img = fctx.createImageData(w, h);
  const bias = parseFloat(lightnessBias.value)/100;
  for (let y=0; y<h; y++) {
    for (let x=0; x<w; x++) {
      const s = x/(w-1);
      const baseV = 1 - y/(h-1);
      const v = Math.max(0, Math.min(1, baseV * 0.75 + bias * 0.25));
      const [r,g,b] = hsvToRgb(hue, s, v);
      const idx = (y*w + x)*4;
      img.data[idx] = r;
      img.data[idx+1] = g;
      img.data[idx+2] = b;
      img.data[idx+3] = 255;
    }
  }
  fctx.putImageData(img, 0, 0);
  const px = sat * w;
  const py = (1 - val) * h;
  fctx.strokeStyle = 'rgba(255,255,255,.95)';
  fctx.lineWidth = 3;
  fctx.beginPath();
  fctx.arc(px, py, 10, 0, Math.PI*2);
  fctx.stroke();
  fctx.strokeStyle = 'rgba(0,0,0,.45)';
  fctx.lineWidth = 1;
  fctx.beginPath();
  fctx.arc(px, py, 12, 0, Math.PI*2);
  fctx.stroke();
}
function targetHex() {
  const bias = parseFloat(lightnessBias.value)/100;
  const v = Math.max(0, Math.min(1, val * 0.75 + bias * 0.25));
  const [r,g,b] = hsvToRgb(hue, sat, v);
  return rgbToHex(r,g,b);
}
function updateMatches() {
  const hex = targetHex();
  const rgb = hexToRgb(hex);
  const lab = rgbToLab(rgb);
  const matches = enriched.map(r => ({ rec:r, d: labDistance(lab, r.lab) }))
    .sort((a,b) => a.d - b.d)
    .slice(0, 12);
  preview.style.background = hex;
  readout.innerHTML = `<div><strong>Target</strong> ${hex}</div><div>Hue ${hue.toFixed(0)}° · Sat ${(sat*100).toFixed(0)} · Val ${(val*100).toFixed(0)}</div>`;
  matchesEl.innerHTML = matches.map(m => `
    <div class="match">
      <div class="match-swatch" style="background:${m.rec.hex}"></div>
      <div>
        <div class="match-name">${m.rec.name}</div>
        <div class="match-meta">${m.rec.brand} ${m.rec.code} · ${m.rec.hex} · Δ≈${m.d.toFixed(1)}</div>
      </div>
    </div>
  `).join('');
}
function redraw() { drawHue(); drawField(); updateMatches(); }

function bindCanvas(canvas, handler) {
  let down = false;
  const apply = e => {
    const rect = canvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, e.clientY - rect.top));
    handler(x/rect.width, y/rect.height);
  };
  canvas.addEventListener('pointerdown', e => { down = true; apply(e); });
  window.addEventListener('pointermove', e => { if (down) apply(e); });
  window.addEventListener('pointerup', () => down = false);
}

bindCanvas(hueCanvas, (_x, y) => { hue = Math.max(0, Math.min(359.999, y*360)); redraw(); });
bindCanvas(field, (x, y) => { sat = Math.max(0, Math.min(1, x)); val = Math.max(0, Math.min(1, 1-y)); redraw(); });
lightnessBias.addEventListener('input', redraw);
redraw();
</script>
</body>
</html>
'''


def main():
    records = load_records()
    html = HTML_TEMPLATE.replace('__RECORDS_JSON__', json.dumps(records))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding='utf-8')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
