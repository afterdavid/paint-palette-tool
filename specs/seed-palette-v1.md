# Seed Palette V1 Spec

## Goal

Define the first practical dataset that will drive the initial `.ase` swatch library.

This is not the final universal paint catalog. It is the first usable palette for real mural work.

## Strategy

Start with a curated palette, not a full ingest of every paint brand.

Reasons:
- faster to build
- easier to validate in real design work
- avoids getting blocked on perfect brand coverage
- good enough to prove the workflow

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
1. manually curated starter set
2. official brand references where easy to obtain
3. reference/fallback sources only to fill specific gaps

This keeps the project moving without pretending the source data is perfect.

## Acceptance criteria

Seed Palette V1 is ready when:
- there is a JSON file with 64 to 128 real entries
- each entry validates against the schema
- each entry has a category and provenance
- the palette can be turned into an `.ase`
- the resulting swatch library feels usable in Illustrator
