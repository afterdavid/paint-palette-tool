# PPG import notes — 2026-04-21

## What changed

Added a PPG catalog importer:
- `scripts/importers/import_ppg.py`

Normalized output:
- `data/catalogs/ppg.json`

Raw/provenance output:
- `data/raw/ppg/sitemap.xml`
- `data/raw/ppg/detail-urls.txt`
- `data/raw/ppg/detail-pages.jsonl`

Generated Adobe output:
- `ase/ppg-full.ase`

## Source used

The importer uses first-party PPG Paints public pages:
- sitemap: `https://www.ppgpaints.com/sitemap.xml`
- detail pages: `https://www.ppgpaints.com/ppg-colors/<slug>`

Each usable detail page exposes:
- display name
- PPG/Dulux-style color code
- RGB values
- LRV, when present

## Result

- sitemap color URLs found: 3,267
- pages fetched: 3,267
- normalized records written: 3,225
- skipped pages: 42

The skipped pages exposed a name/code but no parseable RGB block. Most appear to be specialty or metallic records. They were not added because the canonical color schema requires an RGB preview value, and fabricating color values would make the database less trustworthy.

## Downloadable palette caveat

PPG's official downloadable palette page still links:
- `VOC-ColorNumber-2022.aco`
- `VOC-ColorNumber-2022.ase`
- `ppg-voice-of-colour-palette_rgb-and-lrv-values.xlsx`

Those linked hosts did not resolve from this machine during this pass, even though the page itself was reachable. The detail-page importer is therefore the current reliable PPG path.

## Validation

After this pass:
- all normalized catalog JSON files passed required-field, unknown-field, RGB, and duplicate-id checks
- `ase/ppg-full.ase` parsed back successfully with 3,225 swatches
