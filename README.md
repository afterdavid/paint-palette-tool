# Paint Palette Tool

Adobe-native palette constraint and paint-spec export tool for muralists.

## Goal

Help muralists design with colors that real paint stores can reproduce, then export a paint-store-ready materials/spec sheet.

In practice, the tool has two halves:
- a constrained Adobe swatch library (`.ase`) for color picking
- Illustrator-first scripts that scan artwork and export used colors

## Current status

This repo now has normalized catalog data and generated Adobe swatch outputs.

The source idea/spec came from:
- `specs/source-spec.md`

Initial build direction:
1. define the canonical color schema
2. build a small seed dataset
3. generate the first `.ase` swatch library
4. build Illustrator V1 commands:
   - Refresh Used Colors
   - Export Paint Spec

Catalogs currently include Behr, Glidden, PPG, Dunn-Edwards, Valspar, and partial/native or official downloadable Sherwin-Williams and Benjamin Moore sources.

Primary combined outputs:
- `data/catalogs/paint-store-accessible.json`
- `ase/paint-store-accessible.ase`

## Planned repo layout

- `data/` — normalized color catalogs and schema
- `ase/` — generated Adobe Swatch Exchange files
- `scripts/illustrator/` — Illustrator scripts
- `scripts/photoshop/` — later Photoshop scripts
- `specs/` — product and technical specs
- `samples/` — test files
- `output/` — generated export examples

## Product principles

- Use native Illustrator swatches first.
- Do not replace Illustrator's normal color-picking workflow in V1.
- Track colors by scanning current artwork, not by logging every click.
- Export only colors actually in use at export time.
- Keep output structured first, pretty second.

## First milestone

**Palette in, spec out**

Definition:
- artist loads a constrained palette into Illustrator
- artist uses those swatches in a comp
- script scans the document
- tool outputs a usable materials/spec summary
