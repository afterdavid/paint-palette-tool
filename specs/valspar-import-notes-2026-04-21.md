# Valspar import notes — 2026-04-21

## Official sources reviewed

### Core catalog source
- `https://www.valspar.com/en/colors/browse-colors`

### Official professional / curated color sources
- `https://www.valspar.com/en/professionals/color-toolkit`
- `https://www.valspar.com/en/professionals/interior-neutrals`
- `https://www.valspar.com/en/professionals/exterior-color-combinations`
- `https://www.valspar.com/en/professionals/find-a-rep`

### Discovery support
- `https://www.valspar.com/en.sitemap.xml`
- `https://www.valspar.com/robots.txt`

## What this pass found
- The existing official `browse-colors` wall remains the strongest structured first-party catalog source for Valspar color records.
- I did **not** find a public downloadable digital color library file on the official Valspar site in this pass:
  - no ASE
  - no ACO
  - no ACB
  - no ZIP color library download
  - no PDF fan deck / palette download surfaced from the sitemap or the professional pages inspected
- The official professional section does expose curated, publicly accessible color selections:
  - `interior-neutrals` links a small set of featured colors
  - `exterior-color-combinations` links a larger curated set of featured colors
- The `color-toolkit` landing page itself appears to be editorial/navigation content rather than a downloadable asset page.
- The professional section explicitly references a **physical** fan deck, but only through rep contact (`Find My Rep`), not a public digital download.

## Raw captures added/updated
- `data/raw/valspar/browse-colors.html`
- `data/raw/valspar/color-toolkit.html`
- `data/raw/valspar/interior-neutrals.html`
- `data/raw/valspar/exterior-color-combinations.html`
- `data/raw/valspar/professional-palettes.parsed.json`
- `data/raw/valspar/provenance.json`

## Normalized output

### Main catalog
- `data/catalogs/valspar.json`

This continues to represent the official first-party browseable Valspar color catalog captured from the `browse-colors` wall markup.

### Derived companion catalog
- `data/catalogs/valspar-professional-curated.json`

This file contains color records for the official curated professional subsets. These are **derived** records, not a separate native manufacturer catalog, because:
- the professional pages link to browse-colors detail pages rather than exposing a standalone machine-readable swatch file
- RGB/LAB values were resolved by matching those linked colors back to the official main Valspar catalog capture

## Completeness / caveats
- I would describe `valspar.json` as imported from the currently published official browse-colors page, not as a claim of total historical completeness.
- I would describe `valspar-professional-curated.json` as a capture of the official public professional curated pages found in the current sitemap, not as an exhaustive set of all Valspar editorial palettes ever published.
- The absence of a downloadable official digital swatch file is only a finding for this pass, not proof that one never existed elsewhere historically or behind rep/customer flows.
