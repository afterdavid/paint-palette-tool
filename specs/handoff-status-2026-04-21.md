# Paint Palette Tool handoff status — 2026-04-21

Repo:
- `/Users/theo/apps/paint-palette-tool`

## Current usable outputs

- Combined catalog: `data/catalogs/paint-store-accessible.json`
- Combined Adobe swatch file: `ase/paint-store-accessible.ase`
- Per-brand swatch files: `ase/*-full.ase`, `ase/*-downloadable.ase`, and partial SW/BM files

`paint-store-accessible` means the current best merged set of colors that can be named at a paint counter or used as a paint-store-recognizable target. It uses one best source per target brand, favoring fuller official/catalog or official downloadable sources over partial crawls.

## Coverage

| Brand | Source layer | Records | Notes |
|---|---:|---:|---|
| Behr | official catalog | 5,692 | deduped first-party ColorSmart payload |
| Glidden | official catalog | 3,271 | official sitemap/detail pages |
| PPG Paints | official catalog | 3,225 | official sitemap/detail pages; 42 pages skipped with no RGB |
| Dunn-Edwards | official catalog | 1,923 | official digital swatch assets |
| Valspar | official catalog | 2,858 | official browse-colors page |
| Sherwin-Williams | official downloadable | 1,726 | official ASE downloads; not claimed as full live catalog |
| Benjamin Moore | official downloadable | 4,056 | official ASE downloads; not claimed as exact full live catalog |
| Combined | best-current merged | 22,751 | one current best source per target brand |

Regenerate the table with:

```bash
python3 scripts/catalog_report.py
```

## Build / validate

Build combined catalog:

```bash
python3 scripts/build_accessible_catalog.py
```

Generate ASE:

```bash
python3 scripts/generate_ase.py data/catalogs/paint-store-accessible.json ase/paint-store-accessible.ase
```

The latest validation checked:
- required fields
- unknown fields
- duplicate ids
- RGB hex shape
- ASE parseback counts

Result: 0 catalog validation errors.

## Known caveats

- PPG's official downloadable ASE/ACO/XLS links are present on the PPG page, but their linked hosts did not resolve from this machine. The current PPG catalog therefore uses official sitemap/detail pages.
- 42 PPG pages expose a color page but no parseable RGB block; they are listed in `specs/missing-uncertain-colors-2026-04-21.md`.
- Sherwin-Williams and Benjamin Moore are strongest through official downloadable ASE libraries right now. The native detail-page crawls remain partial and are not used in the combined catalog.
- Adobe Illustrator is not installed under `/Applications` on this machine, so the practical Illustrator import smoke test could not be run here. Binary ASE parseback succeeded locally.

## Next product step

Build the Illustrator V1 script around native Swatches:
- scan current document
- list used swatches
- warn on ad hoc colors outside `paint-store-accessible`
- export JSON/CSV before PDF
