# Behr + Glidden import notes — 2026-04-21

## Behr

### Official source found
- `https://www.behr.com/mainrefreshservice/services/color2019/all.js`

### What it contains
- a global `colorData` array with field headers in row 0
- 6,268 color rows imported in this pass
- fields include:
  - `id`
  - `name`
  - `rgb`
  - `a`
  - `b`
  - `luminosity`
  - adjacency fields like `next`, `prev`, `friend`
  - several catalog flags (`isbasic`, `islegacycolor`, `israck`, `israckultra`, `isultra`)

### Raw capture
- `data/raw/behr/all.js`
- `data/raw/behr/all.parsed.json`

### Normalized output
- `data/catalogs/behr.json`

### Notes
- This appears to be the strongest source among the two brands: first-party, structured, and large enough to look like a real full catalog payload.
- LAB values in the normalized file use Behr's own `a`, `b`, and `luminosity` fields.

## Glidden

### Official sources found
- `https://www.glidden.com/sitemap.xml`
- homepage inline search config exposing Algolia app/key/index:
  - app: `EU3MF6Q69W`
  - index: `prd_Glidden11Colors`
- official detail pages under `https://www.glidden.com/colors/<slug>`

### What they contain
- sitemap listed 3,271 color detail pages in this pass
- detail pages expose:
  - title with display name + brand code
  - description text
  - `data-rgb` swatch values
- Algolia index returned 3,250 hits and is useful supplemental metadata, but it is not the authoritative URL inventory because sitemap count is higher

### Raw capture
- `data/raw/glidden/homepage.html`
- `data/raw/glidden/algolia-config.json`
- `data/raw/glidden/sitemap.xml`
- `data/raw/glidden/algolia-page-0.json` ... `algolia-page-3.json`
- `data/raw/glidden/details.parsed.json`

### Normalized output
- `data/catalogs/glidden.json`

### Notes
- Some Glidden colors use legacy/non-PPG code formats like `58RR 45/306`; the importer preserves those exact strings as `brandCode`.
- LAB values for Glidden are computed from the official RGB swatch values because the pages did not expose LAB directly.
- Algolia-family tags only populate when a sitemap URL also appears in the Algolia index; some legacy colors therefore have empty `tags`.

## Importer script added
- `scripts/importers/import_behr_glidden.py`

### Current behavior
- fetches official source material
- stores raw captures under `data/raw/`
- normalizes Behr and Glidden into canonical catalog JSON
- performs lightweight schema-shape validation

## Remaining caveats
- Glidden completeness looks good from the sitemap, but I would still describe it as "imported from the currently published official sitemap" rather than claiming eternal/full historical completeness.
- The repo also has other in-progress catalog files and raw folders unrelated to this pass; they were left alone.
