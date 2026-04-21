# Seed Palette V1 Spec

## Goal

Define the first practical output palette that will drive the initial `.ase` swatch library.

This document no longer describes the canonical dataset for the whole project. The canonical dataset is now expected to grow toward full manufacturer catalogs.

Instead, this document describes the first curated output subset generated from the larger catalog layer.

## Strategy

Use a two-layer model:
- full manufacturer catalogs as the canonical data layer
- curated output palettes as the Illustrator UX layer

This keeps the long-term dataset complete without forcing artists to work from one giant wall of swatches.

## Size target

Recommended first size:
- 64 to 128 colors

This is large enough to be useful and small enough to stay legible in Illustrator.

## Category targets

The first seed palette should overrepresent common mural needs.

Suggested buckets:
- off-whites / whites
- warm neutrals
- cool neutrals
- charcoals / blacks
- sky blues
- water blues
- foliage greens
- yellow-greens
- warm yellows
- oranges / rusts
- reds / maroons
- pinks / skin-adjacent tones
- violets used in shadowing
- masonry / dirt / earth browns
- accent brights that are actually reproducible in paint

## Selection rules

Each seed color should satisfy most of these:
- visibly distinct from nearby palette neighbors
- plausible for real mural use
- reproducible by common house-paint workflows
- useful either as a local color or a mixing/reference anchor
- simple enough to name and recognize quickly

Avoid in V1:
- ultra-fine gradients of almost-identical colors
- edge-case neons that are not actually reproducible
- obscure catalog completeness for its own sake

## Data fields required

Every seed record should include:
- `id`
- `displayName`
- `brand`
- `brandCode`
- `rgbHex`
- `lab`
- `source.kind`
- `stockMatchable`
- `tags`

Strongly recommended extra fields:
- `category`
- `notes`
- `priority`

## Naming rules

Display names should be practical, not poetic.

Good:
- `Warm White 01`
- `Sky Blue 03`
- `Foliage Green 02`
- `Rust 01`

Avoid:
- long brand-marketing names as the primary user-facing label

Brand names/codes should still be preserved in metadata.

## Provenance policy

Every color must carry provenance.

Allowed source kinds:
- `official`
- `manual`
- `reference`
- `derived`

If the dataset uses approximated or hand-entered values, that should be explicit.

## V1 sourcing plan

Recommended order:
1. normalize manufacturer catalogs into canonical files
2. preserve provenance for every record
3. generate the first curated Illustrator subset from those catalogs
4. use reference/fallback sources only to fill specific gaps

This keeps the UX manageable while still aiming at full brand coverage.

## Acceptance criteria

Seed Palette V1 is ready when:
- there is a curated JSON output file with 64 to 128 real entries
- each entry is traceable back to the canonical catalog data
- each entry validates against the schema
- each entry has category and provenance
- the palette can be turned into an `.ase`
- the resulting swatch library feels usable in Illustrator
