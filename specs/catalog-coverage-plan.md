# Catalog Coverage Plan

## New requirement

The tool should eventually include every color offered by the target manufacturers, not just a curated starter subset.

Target libraries called out as most portable/useful:
- Behr / Glidden — native
- Sherwin-Williams — universal
- Benjamin Moore — universal
- Dunn-Edwards — usually available through competitor libraries
- Valspar — usually available through competitor libraries

## What this changes

This means the project has two palette layers, not one.

### Layer 1 — full manufacturer catalogs
This is the canonical data layer.

Purpose:
- preserve the full usable paint universe
- support search by brand, code, and name
- let artists work from real store-recognizable colors
- support later nearest-match logic across libraries

### Layer 2 — curated working subsets
This is the UX layer.

Purpose:
- keep Illustrator usable
- avoid forcing artists to scroll through thousands of colors at once
- provide practical subsets for mural work

Examples:
- full Sherwin-Williams library
- full Benjamin Moore library
- full Behr library
- universal mural subset
- neutrals subset
- skies subset
- foliage subset

## Recommended product behavior

The dataset should contain full catalogs.
The default Illustrator experience should still prefer manageable subsets.

That means:
- importable full-brand libraries exist
- importable curated subsets also exist
- users can choose between completeness and speed

## Data model implications

Canonical color records now need a few more fields.

Required additions:
- `manufacturer`
- `libraryType` (`native`, `universal`, `competitor`, `derived`)
- `availabilityNotes`
- `aliases` or `alternateNames`
- `catalogOrder` if available
- `active` if colors are discontinued or uncertain

Strongly recommended:
- `sourceConfidence`
- `lastVerifiedAt`
- `regions` if some lines are region-specific

## UX implications for Illustrator

Do not load every manufacturer color into one giant undifferentiated palette by default.

That would be miserable to use.

Better options:
- separate `.ase` per manufacturer
- curated cross-brand subsets
- later: searchable panel/plugin wrapper

### Good V1/V2 palette outputs
- `behr-full.ase`
- `glidden-full.ase`
- `sherwin-williams-full.ase`
- `benjamin-moore-full.ase`
- `dunn-edwards-full.ase`
- `valspar-full.ase`
- `universal-mural-core.ase`

## Data acquisition strategy

The hard part is no longer just schema. It is acquisition and normalization.

Recommended order:
1. define canonical schema for full catalogs
2. create one normalized catalog file per manufacturer
3. preserve provenance for every record
4. generate derived `.ase` outputs from normalized data
5. only after that, build the richer Illustrator helper layer

## Operational rule

The system should never pretend uncertain data is exact.

If a color is:
- scraped from a brand page
- inferred from a competitor library
- copied from a third-party reference
- manually entered

that provenance should be explicit.

## Immediate next step

Revise the schema and seed-palette plan so they support:
- full-catalog ingestion
- multiple output libraries
- curated subsets generated from the same canonical dataset
