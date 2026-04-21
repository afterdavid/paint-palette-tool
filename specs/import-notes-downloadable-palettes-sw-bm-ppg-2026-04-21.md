# Downloadable palette import notes — Sherwin-Williams / Benjamin Moore / PPG — 2026-04-21

## What this pass changed

This recovery pass used **official downloadable palette pages/assets** instead of fragile color-detail crawling.

Outputs were kept separate from canonical manufacturer catalog files:
- normalized downloadable-palette outputs: `data/catalogs/downloadable-palettes/`
- raw captures + manifests: `data/raw/<manufacturer>/downloadable-palettes/`

That separation matters because these sources are best understood as **official downloadable library/palette collections**, not automatically verified full manufacturer catalogs.

## Sherwin-Williams

Official page:
- `https://www.sherwin-williams.com/painting-contractors/color/color-tools/downloadable-color-palettes`

Raw captures saved:
- `data/raw/sherwin-williams/downloadable-palettes/download-page.html`
- `data/raw/sherwin-williams/downloadable-palettes/sw-colors-number-csp-ase.ase`
- `data/raw/sherwin-williams/downloadable-palettes/sw-colors-number-ede-ase.ase`
- `data/raw/sherwin-williams/downloadable-palettes/sw-colorsnap-coll-by-number.zip`
- `data/raw/sherwin-williams/downloadable-palettes/sw-ede-coll-by-number.zip`
- `data/raw/sherwin-williams/downloadable-palettes/manifest.json`

Normalized output:
- `data/catalogs/downloadable-palettes/sherwin-williams.json`

What was extracted:
- **1,726 unique records** from official ASE downloads
- palette membership tags preserved:
  - `palette:ColorSnap Collection` → 1,526
  - `palette:Designer Color Collection` → 200

Practical interpretation:
- This is a strong official downloadable-library source.
- It is useful for Illustrator/Adobe workflows immediately.
- It still should **not** be described as verified complete Sherwin-Williams catalog coverage without an explicit official completeness claim.

## Benjamin Moore

Official page:
- `https://www.benjaminmoore.com/en-us/architects-designers/download-benjamin-moore-color-palettes`

Raw captures saved:
- `data/raw/benjamin-moore/downloadable-palettes/download-page.html`
- 11 official ASE downloads under `data/raw/benjamin-moore/downloadable-palettes/`
- `data/raw/benjamin-moore/downloadable-palettes/manifest.json`

Normalized output:
- `data/catalogs/downloadable-palettes/benjamin-moore.json`

What was extracted:
- **4,056 unique records** across the official downloadable ASE collections
- palette tags preserved, including:
  - `palette:classiccolors` → 1,680
  - `palette:colorpreview` → 1,232
  - `palette:colorstories` → 240
  - `palette:designerclassics` → 231
  - `palette:historicalcolors` → 191
  - `palette:off-whitecolors` → 152
  - `palette:affinity` → 144
  - `palette:williamsburgcolorcollection` → 144
  - `palette:colorsforvinylsiding` → 75
  - `palette:americascolors` → 42
  - `palette:ColorTrends2026` → 8

Practical interpretation:
- These downloads are much more robust than throttled detail-page crawling.
- They appear to cover a very large official Benjamin Moore downloadable color universe.
- However, because these are collection downloads and the unique total exceeds the site's simpler marketing claim of "3,500+ hues," this pass should **not** claim verified exact full-catalog coverage yet.
- Best wording: **official downloadable palette/library coverage with large-scale extraction**, not guaranteed one-to-one catalog completeness.

## PPG

Official page:
- `https://www.ppgpaints.com/designers/professional-color-tools/palette-downloads`

Raw captures saved:
- `data/raw/ppg/downloadable-palettes/download-page.html`
- `data/raw/ppg/downloadable-palettes/manifest.json`

Official asset links extracted from the page:
- `VOC-ColorNumber-2022.aco`
- `VOC-ColorNumber-2022.ase`
- `ppg-voice-of-colour-palette_rgb-and-lrv-values.xlsx`

What happened in this environment:
- The official page was fetchable.
- The linked binary/data assets pointed to Azure/Blob hosts that were **not DNS-resolvable from this environment** during this pass.
- Therefore no PPG normalized color-record file was written from downloadable assets.

Practical interpretation:
- We have official PPG downloadable-source provenance and exact asset URLs.
- We have importer groundwork ready to parse `.ACO`, `.ASE`, and record spreadsheet metadata once downloads succeed.
- We do **not** have verified extracted PPG palette records from those downloadable files yet.

## Importer added

New script:
- `scripts/import_downloadable_palettes.py`

Current behavior:
- downloads/captures official SW/BM/PPG downloadable palette pages
- downloads SW and BM official palette assets
- parses official `.ASE` files into normalized source-derived records
- attempts PPG linked downloads and records failures honestly in the manifest

## Recommendation

Treat these outputs as a new layer:
- **downloadable official palette libraries** for Adobe/design-tool interoperability

Do not merge them blindly into the canonical manufacturer catalog files yet.

They are extremely useful, but their semantic role is slightly different:
- better for portable swatch-library ingestion
- not automatically identical to a brand's full live retail catalog
