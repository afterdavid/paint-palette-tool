# Schema and provenance

## Canonical record

Each color record follows `data/color-schema.json`.

Key fields:
- `id`: stable internal id, usually `manufacturer-code-name` or the imported library's stable equivalent
- `displayName`: user-facing color name
- `manufacturer`: paint company name
- `brand`: brand/library name used at the counter
- `brandCode`: counter-recognizable color code
- `libraryType`: `native`, `universal`, `competitor`, or `derived`
- `rgbHex`: RGB preview value used for Adobe swatches
- `lab`: computed or source-provided LAB value
- `lrv`: light reflectance value when exposed by the source
- `source`: source kind, URL, and notes
- `sourceConfidence`: current confidence level
- `availabilityNotes`: caveats about completeness, region, or source limitations

## Provenance rules

- Prefer first-party manufacturer sources.
- Keep source scope explicit. A downloadable ASE library is not automatically the same thing as a full retail catalog.
- Do not fabricate RGB/LAB values for pages that lack color data.
- Preserve raw captures under `data/raw/<manufacturer>/` when an importer relies on crawl or download behavior.
- Put derived or source-scoped libraries under `data/catalogs/downloadable-palettes/` when they are useful but semantically different from a live catalog.

## Dedupe rules

- Within a manufacturer, `brandCode` is the practical identity used at the paint counter.
- For the combined catalog, keep one best-current source per `manufacturer::brandCode`.
- Prefer fuller official sources over partial crawls.
- Behr duplicates from the ColorSmart payload are deduped by stable internal `id`.
- Partial Benjamin Moore and Sherwin-Williams crawls are retained for provenance, but the combined catalog uses their official downloadable ASE outputs.

## Current combined-source selection

`scripts/build_accessible_catalog.py` currently merges:
- `data/catalogs/behr.json`
- `data/catalogs/glidden.json`
- `data/catalogs/ppg.json`
- `data/catalogs/dunn-edwards.json`
- `data/catalogs/valspar.json`
- `data/catalogs/downloadable-palettes/sherwin-williams.json`
- `data/catalogs/downloadable-palettes/benjamin-moore.json`
